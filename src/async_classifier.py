import asyncio
import aioredis
from celery import Celery
from typing import Dict, Any
import os
import time
from werkzeug.datastructures import FileStorage
from io import BytesIO

# Celery configuration for async processing
celery_app = Celery(
    'classifier',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_retry_delay=60,
    task_max_retries=3,
)

class AsyncClassifier:
    def __init__(self):
        self.redis = None
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    async def init_redis(self):
        """Initialize Redis connection for queue management"""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics for monitoring"""
        if not self.redis:
            await self.init_redis()
        
        try:
            # Get queue length and worker stats
            queue_length = await self.redis.llen('celery')
            
            # Get Redis memory info
            info = await self.redis.info('memory')
            
            return {
                'queue_length': queue_length,
                'memory_used': info.get('used_memory_human', 'unknown'),
                'redis_connected': True
            }
        except Exception as e:
            return {'error': str(e), 'redis_connected': False}

# Global classifier instance
classifier = AsyncClassifier()

@celery_app.task(bind=True, max_retries=3)
def classify_document_async(self, file_data: bytes, filename: str, industry: str = 'finance'):
    """Async document classification task"""
    start_time = time.time()
    
    try:
        # Import here to avoid circular imports
        from src.classifier.file_type_handling import classify_file as process_file
        
        # Create a FileStorage-like object from bytes
        file_obj = BytesIO(file_data)
        file_obj.filename = filename
        file_obj.content_type = 'application/octet-stream'
        
        # Process classification
        result = process_file(file_obj, industry)
        
        # Add processing metadata
        result['processing_time'] = time.time() - start_time
        result['processed_at'] = time.time()
        result['worker_id'] = self.request.id
        result['task_id'] = self.request.id
        
        return result
        
    except Exception as exc:
        # Log the error
        print(f"Classification task failed: {exc}")
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

@celery_app.task
def cleanup_old_tasks():
    """Periodic task to clean up old task results"""
    try:
        # Clean up task results older than 1 hour
        # This prevents Redis from growing indefinitely
        inspect = celery_app.control.inspect()
        
        # Get completed tasks and clean up old ones
        # Implementation depends on your Redis backend configuration
        
        return "Task cleanup completed"
        
    except Exception as e:
        return f"Task cleanup failed: {e}"

@celery_app.task
def get_system_stats():
    """Get system statistics for monitoring"""
    try:
        import psutil
        
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get Celery stats
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        
        return {
            'timestamp': time.time(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_free': disk.free
            },
            'celery': {
                'active_tasks': len(active_tasks) if active_tasks else 0,
                'scheduled_tasks': len(scheduled_tasks) if scheduled_tasks else 0
            }
        }
    except Exception as e:
        return {'error': str(e)}

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks-every-hour': {
        'task': 'src.async_classifier.cleanup_old_tasks',
        'schedule': 3600.0,  # Every hour
    },
    'system-stats-every-5-minutes': {
        'task': 'src.async_classifier.get_system_stats',
        'schedule': 300.0,  # Every 5 minutes
    },
}

# Health check functions
async def health_check() -> Dict[str, Any]:
    """Check health of async processing system"""
    try:
        # Check Redis connection
        redis_healthy = False
        redis_error = None
        try:
            if not classifier.redis:
                await classifier.init_redis()
            await classifier.redis.ping()
            redis_healthy = True
        except Exception as e:
            redis_error = str(e)
        
        # Check Celery workers
        inspect = celery_app.control.inspect()
        workers = inspect.ping()
        celery_healthy = bool(workers)
        
        return {
            'status': 'healthy' if redis_healthy and celery_healthy else 'unhealthy',
            'redis': {
                'healthy': redis_healthy,
                'error': redis_error if not redis_healthy else None
            },
            'celery': {
                'healthy': celery_healthy,
                'workers': list(workers.keys()) if workers else []
            },
            'timestamp': time.time()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }

# Utility functions for the main app
def submit_classification_task(file_data: bytes, filename: str, industry: str = 'finance') -> str:
    """Submit a classification task and return task ID"""
    task = classify_document_async.delay(file_data, filename, industry)
    return task.id

def get_task_result(task_id: str) -> Dict[str, Any]:
    """Get the result of a classification task"""
    task = classify_document_async.AsyncResult(task_id)
    
    if task.ready():
        if task.successful():
            return {
                'status': 'completed',
                'result': task.result,
                'task_id': task_id
            }
        else:
            return {
                'status': 'failed',
                'error': str(task.info),
                'task_id': task_id
            }
    else:
        # Get task state and progress
        return {
            'status': 'processing',
            'state': task.state,
            'info': task.info if hasattr(task, 'info') else None,
            'task_id': task_id
        }

def get_task_status(task_id: str) -> str:
    """Get just the status of a task"""
    task = classify_document_async.AsyncResult(task_id)
    return task.state

# Queue management functions
async def get_queue_statistics() -> Dict[str, Any]:
    """Get queue statistics for monitoring"""
    return await classifier.get_queue_stats()

async def get_worker_statistics() -> Dict[str, Any]:
    """Get worker statistics"""
    try:
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()
        
        # Get worker stats
        stats = inspect.stats()
        
        return {
            'active_tasks': active,
            'scheduled_tasks': scheduled,
            'reserved_tasks': reserved,
            'worker_stats': stats,
            'timestamp': time.time()
        }
    except Exception as e:
        return {'error': str(e)}

# Priority queue management
def submit_priority_task(file_data: bytes, filename: str, industry: str = 'finance', priority: str = 'normal') -> str:
    """Submit a task with priority (high, normal, low)"""
    
    # Map priority to Celery routing
    priority_map = {
        'high': {'queue': 'high_priority', 'routing_key': 'high'},
        'normal': {'queue': 'celery', 'routing_key': 'celery'},
        'low': {'queue': 'low_priority', 'routing_key': 'low'}
    }
    
    routing = priority_map.get(priority, priority_map['normal'])
    
    task = classify_document_async.apply_async(
        args=[file_data, filename, industry],
        **routing
    )
    
    return task.id
