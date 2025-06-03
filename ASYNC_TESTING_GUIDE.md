# Async Classifier Testing Guide

## What You Actually Need

### **Essential Components:**
1. **Redis** - Message broker for task queue
2. **Celery Worker** - Processes classification tasks
3. **Your Flask App** - Receives requests and submits tasks

### **Optional Components:**
- **PostgreSQL** - Only for analytics/monitoring (skip for testing)
- **Complex monitoring** - Only for production (skip for testing)

## Quick Test Setup (5 minutes)

### Step 1: Start Redis
```bash
# Option A: Docker (easiest)
docker run -d -p 6379:6379 --name redis redis:alpine

# Option B: Local Redis (if installed)
redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### Step 2: Start Celery Worker
```bash
# In your project directory
celery -A src.simple_async_classifier.celery_app worker --loglevel=info

# You should see:
# [2024-06-02 15:30:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
# [2024-06-02 15:30:00,000: INFO/MainProcess] mingle: searching for neighbors
# [2024-06-02 15:30:00,000: INFO/MainProcess] celery@hostname ready.
```

### Step 3: Test Async Classifier
```bash
# Run the test script
python test_async_classifier.py

# Expected output:
# 🧪 Async Classifier Test Suite
# 🔍 Testing Async Classifier
# 1. Checking Celery workers...
#    Status: healthy
#    Workers: ['celery@your-hostname']
# 2. Submitting classification task...
#    Task submitted: abc123-def456-789
# 3. Waiting for results...
#    Status: processing
#    Status: completed
# ✅ Classification completed!
#    Classification: invoice
#    Confidence: 0.95
#    Processing time: 45.23s
```

## What Each Function Does (Simplified)

### **Essential Functions (Keep These):**

```python
# 1. The main task - does the actual classification
@celery_app.task
def classify_document_async(file_data, filename, industry):
    # Converts bytes to FileStorage object
    # Calls your existing classifier
    # Returns result

# 2. Submit a task - used by Flask app
def submit_classification_task(file_data, filename, industry):
    # Puts task in Redis queue
    # Returns task ID

# 3. Get task result - used by Flask app
def get_task_result(task_id):
    # Checks if task is done
    # Returns result or status

# 4. Health check - used by monitoring
def simple_health_check():
    # Checks if workers are running
```

### **Optional Functions (Can Remove):**

```python
# These are nice-to-have but not essential:
- get_queue_statistics()      # Monitoring
- get_worker_statistics()     # Monitoring  
- submit_priority_task()      # Advanced queuing
- cleanup_old_tasks()         # Maintenance
- get_system_stats()          # System monitoring
```

## Testing Without Flask App

If you just want to test the async classifier directly:

```python
# test_simple.py
from src.simple_async_classifier import (
    submit_classification_task,
    get_task_result,
    simple_health_check
)
import time

# Check workers
print("Workers:", simple_health_check())

# Submit task
with open('files/invoice_1.pdf', 'rb') as f:
    file_data = f.read()

task_id = submit_classification_task(file_data, 'invoice_1.pdf', 'finance')
print(f"Task ID: {task_id}")

# Wait for result
while True:
    result = get_task_result(task_id)
    print(f"Status: {result['status']}")
    
    if result['status'] == 'completed':
        print("Result:", result['result'])
        break
    elif result['status'] == 'failed':
        print("Error:", result['error'])
        break
    
    time.sleep(5)
```

## Common Issues & Solutions

### ❌ "No Celery workers running"
**Problem**: Worker not started or Redis not running
**Solution**: 
```bash
# Check Redis
redis-cli ping

# Start worker
celery -A src.simple_async_classifier.celery_app worker --loglevel=info
```

### ❌ "Connection refused to Redis"
**Problem**: Redis not running or wrong URL
**Solution**:
```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Or check REDIS_URL environment variable
echo $REDIS_URL
```

### ❌ "Task failed with import error"
**Problem**: Circular imports or missing dependencies
**Solution**:
```bash
# Make sure you're in the right directory
cd join-the-siege

# Check if your classifier works synchronously first
python -c "from src.classifier import classify_file; print('Import OK')"
```

### ❌ "Task timeout"
**Problem**: OpenAI API call taking too long
**Solution**:
- Check your OpenAI API key is set: `echo $OPENAI_API_KEY`
- Test sync classifier first: `python test_api.py`
- Increase task timeout in Celery config

## Minimal Production Setup

For production, you only need:

```yaml
# docker-compose.minimal.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A src.simple_async_classifier.celery_app worker --loglevel=info
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
```

**Total**: 3 containers, no PostgreSQL needed for basic async processing.

## Why This Works for Scale

### **100k requests/day = ~1.2 requests/second**
- 1 Redis instance: handles 100k+ ops/second
- 2-3 Celery workers: handle 1-2 requests/second each
- 1 Flask instance: submits tasks instantly (no blocking)

### **Traffic spikes handled automatically**
- Requests queue up in Redis
- Workers process at steady rate
- No requests are lost or timeout

This simple setup can easily handle your initial scale without the complexity of PostgreSQL, monitoring, or advanced features.
