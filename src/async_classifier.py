import os
import time
from celery import Celery
from typing import Dict, Any
from io import BytesIO

# Minimal Celery configuration - only Redis needed
celery_app = Celery(
    'classifier',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Basic Celery settings
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_time_limit=300,  # 5 minutes max
    task_max_retries=3,
)

@celery_app.task(bind=True, max_retries=3)
def classify_document_async(self, file_data: bytes, filename: str, industry: str = 'finance'):
    """The only essential function - does the actual classification"""
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
        result['task_id'] = self.request.id
        
        return result
        
    except Exception as exc:
        print(f"Classification task failed: {exc}")
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

# Essential utility functions for Flask app
def submit_classification_task(file_data: bytes, filename: str, industry: str = 'finance') -> str:
    """Submit a task and return task ID"""
    task = classify_document_async.delay(file_data, filename, industry)
    return task.id

def get_task_result(task_id: str) -> Dict[str, Any]:
    """Get the result of a task"""
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
        return {
            'status': 'processing',
            'state': task.state,
            'task_id': task_id
        }

