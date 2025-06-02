# Scaling Architecture for Document Classifier API
## Handling 100k-1M Requests/Day with High Availability

Based on your current LLM + metadata + image classification system achieving 98%+ accuracy, here's a comprehensive scaling strategy.

## Current Architecture Analysis

**Current Setup:**
- Flask API with single endpoint `/classify_file`
- Direct OpenAI API calls (GPT-4o/GPT-4o-mini)
- Synchronous processing
- Single Docker container deployment
- No caching or load balancing

**Bottlenecks for Scale:**
1. **LLM API Rate Limits**: OpenAI has strict rate limits
2. **Single Point of Failure**: One container, one API key
3. **Synchronous Processing**: Blocking requests
4. **No Load Distribution**: All traffic to single instance
5. **No Queue Management**: No handling of traffic spikes

## Scaling Strategy: Multi-Tier Architecture

### Tier 1: Load Balancer & API Gateway (100k-300k req/day)

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - classifier-1
      - classifier-2
      - classifier-3
    restart: unless-stopped

  classifier-1:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY_1}
      - INSTANCE_ID=classifier-1
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres

  classifier-2:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY_2}
      - INSTANCE_ID=classifier-2
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres

  classifier-3:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY_3}
      - INSTANCE_ID=classifier-3
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=classifier_db
      - POSTGRES_USER=classifier
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
```

### Tier 2: Async Processing with Queue (300k-700k req/day)

```python
# src/async_classifier.py
import asyncio
import aioredis
from celery import Celery
from typing import Dict, Any
import hashlib
import json

# Celery configuration for async processing
celery_app = Celery(
    'classifier',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

class AsyncClassifier:
    def __init__(self):
        self.redis = None
        self.cache_ttl = 3600 * 24  # 24 hours
    
    async def init_redis(self):
        self.redis = await aioredis.from_url("redis://redis:6379")
    
    def generate_cache_key(self, file_content: bytes, industry: str) -> str:
        """Generate cache key from file content hash + industry"""
        file_hash = hashlib.sha256(file_content).hexdigest()
        return f"classification:{industry}:{file_hash}"
    
    async def get_cached_result(self, cache_key: str) -> Dict[str, Any]:
        """Check cache for existing classification"""
        if not self.redis:
            await self.init_redis()
        
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache classification result"""
        if not self.redis:
            await self.init_redis()
        
        await self.redis.setex(
            cache_key, 
            self.cache_ttl, 
            json.dumps(result)
        )

# Celery task for async processing
@celery_app.task(bind=True, max_retries=3)
def classify_document_async(self, file_data: bytes, filename: str, industry: str):
    """Async document classification task"""
    try:
        from src.classifier import classify_file_from_bytes
        
        # Process classification
        result = classify_file_from_bytes(file_data, filename, industry)
        
        # Cache result
        classifier = AsyncClassifier()
        cache_key = classifier.generate_cache_key(file_data, industry)
        asyncio.run(classifier.cache_result(cache_key, result))
        
        return result
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# Updated Flask app with async support
from flask import Flask, request, jsonify
import asyncio

app = Flask(__name__)

@app.route('/classify_file_async', methods=['POST'])
def classify_file_async_route():
    """Async classification endpoint"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    industry = request.form.get('industry', 'finance')
    
    # Read file data
    file_data = file.read()
    
    # Check cache first
    classifier = AsyncClassifier()
    cache_key = classifier.generate_cache_key(file_data, industry)
    
    # Try to get cached result
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cached_result = loop.run_until_complete(classifier.get_cached_result(cache_key))
    
    if cached_result:
        return jsonify({
            **cached_result,
            "cached": True,
            "processing_time": 0.1
        }), 200
    
    # Submit to queue for processing
    task = classify_document_async.delay(file_data, file.filename, industry)
    
    return jsonify({
        "task_id": task.id,
        "status": "processing",
        "estimated_time": "30-60 seconds"
    }), 202

@app.route('/classification_result/<task_id>', methods=['GET'])
def get_classification_result(task_id):
    """Get async classification result"""
    
    task = classify_document_async.AsyncResult(task_id)
    
    if task.ready():
        if task.successful():
            return jsonify({
                "status": "completed",
                "result": task.result
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "error": str(task.info)
            }), 500
    else:
        return jsonify({
            "status": "processing",
            "progress": "In queue"
        }), 202
```

### Tier 3: Multi-LLM Provider Strategy (700k-1M+ req/day)

```python
# src/llm_providers.py
import asyncio
import aiohttp
from typing import Dict, List, Any
from enum import Enum
import random

class LLMProvider(Enum):
    OPENAI_GPT4O = "openai_gpt4o"
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    ANTHROPIC_CLAUDE3 = "anthropic_claude3"
    ANTHROPIC_CLAUDE3_HAIKU = "anthropic_claude3_haiku"
    GOOGLE_GEMINI_PRO = "google_gemini_pro"

class LLMLoadBalancer:
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI_GPT4O: {
                "api_keys": [
                    os.getenv('OPENAI_API_KEY_1'),
                    os.getenv('OPENAI_API_KEY_2'),
                    os.getenv('OPENAI_API_KEY_3'),
                    os.getenv('OPENAI_API_KEY_4'),
                    os.getenv('OPENAI_API_KEY_5'),
                ],
                "rate_limit": 10000,  # requests per minute
                "cost_per_1k": 0.005,
                "quality_score": 0.95,
                "current_usage": 0
            },
            LLMProvider.OPENAI_GPT4O_MINI: {
                "api_keys": [
                    os.getenv('OPENAI_MINI_API_KEY_1'),
                    os.getenv('OPENAI_MINI_API_KEY_2'),
                    os.getenv('OPENAI_MINI_API_KEY_3'),
                ],
                "rate_limit": 30000,
                "cost_per_1k": 0.00015,
                "quality_score": 0.92,
                "current_usage": 0
            },
            LLMProvider.ANTHROPIC_CLAUDE3: {
                "api_keys": [
                    os.getenv('ANTHROPIC_API_KEY_1'),
                    os.getenv('ANTHROPIC_API_KEY_2'),
                ],
                "rate_limit": 5000,
                "cost_per_1k": 0.015,
                "quality_score": 0.96,
                "current_usage": 0
            }
        }
    
    def select_optimal_provider(self, priority: str = "cost") -> tuple:
        """Select best provider based on priority and availability"""
        
        available_providers = []
        
        for provider, config in self.providers.items():
            if config["current_usage"] < config["rate_limit"] * 0.8:  # 80% threshold
                available_providers.append((provider, config))
        
        if not available_providers:
            raise Exception("No available LLM providers")
        
        if priority == "cost":
            # Sort by cost (cheapest first)
            available_providers.sort(key=lambda x: x[1]["cost_per_1k"])
        elif priority == "quality":
            # Sort by quality (highest first)
            available_providers.sort(key=lambda x: x[1]["quality_score"], reverse=True)
        elif priority == "speed":
            # Sort by rate limit (fastest first)
            available_providers.sort(key=lambda x: x[1]["rate_limit"], reverse=True)
        
        provider, config = available_providers[0]
        api_key = random.choice(config["api_keys"])
        
        return provider, api_key
    
    async def classify_with_fallback(self, prompt: str, image_data: bytes) -> Dict[str, Any]:
        """Classify with automatic fallback between providers"""
        
        providers_to_try = [
            ("cost", 3),      # Try 3 cheapest providers first
            ("quality", 2),   # Then try 2 highest quality
            ("speed", 1)      # Finally try fastest
        ]
        
        last_error = None
        
        for priority, max_attempts in providers_to_try:
            for attempt in range(max_attempts):
                try:
                    provider, api_key = self.select_optimal_provider(priority)
                    
                    if provider.value.startswith("openai"):
                        result = await self._call_openai(prompt, image_data, api_key)
                    elif provider.value.startswith("anthropic"):
                        result = await self._call_anthropic(prompt, image_data, api_key)
                    elif provider.value.startswith("google"):
                        result = await self._call_google(prompt, image_data, api_key)
                    
                    # Update usage tracking
                    self.providers[provider]["current_usage"] += 1
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
    async def _call_openai(self, prompt: str, image_data: bytes, api_key: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        # Implementation similar to your current llm_call.py
        pass
    
    async def _call_anthropic(self, prompt: str, image_data: bytes, api_key: str) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        # Implementation for Claude
        pass
    
    async def _call_google(self, prompt: str, image_data: bytes, api_key: str) -> Dict[str, Any]:
        """Call Google Gemini API"""
        # Implementation for Gemini
        pass
```

### Tier 4: Kubernetes Deployment for Maximum Scale

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: document-classifier
spec:
  replicas: 10
  selector:
    matchLabels:
      app: document-classifier
  template:
    metadata:
      labels:
        app: document-classifier
    spec:
      containers:
      - name: classifier
        image: your-registry/document-classifier:latest
        ports:
        - containerPort: 5000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: postgres-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: classifier-service
spec:
  selector:
    app: document-classifier
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: classifier-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: document-classifier
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## High Availability Strategy

### 1. **Multi-Region Deployment**
```yaml
# Deploy across multiple regions
regions:
  - us-east-1 (primary)
  - us-west-2 (secondary)
  - eu-west-1 (tertiary)

# Route 53 health checks with failover
route53:
  primary: classifier-us-east.yourdomain.com
  secondary: classifier-us-west.yourdomain.com
  tertiary: classifier-eu-west.yourdomain.com
```

### 2. **Database Replication**
```yaml
# PostgreSQL with read replicas
postgres:
  primary: us-east-1
  read_replicas:
    - us-east-1b
    - us-west-2a
    - eu-west-1a
  
# Redis Cluster for caching
redis:
  cluster_mode: enabled
  nodes: 6
  replicas: 2
```

### 3. **Circuit Breaker Pattern**
```python
# src/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def reset(self):
        self.failure_count = 0
        self.state = "CLOSED"
```

## Performance Metrics & Monitoring

### Key Metrics to Track:
1. **Throughput**: Requests per second
2. **Latency**: P50, P95, P99 response times
3. **Error Rate**: 4xx/5xx responses
4. **LLM Provider Health**: Rate limits, costs, response times
5. **Queue Depth**: Celery task backlog
6. **Worker Utilization**: CPU and memory usage per worker

### Monitoring Stack:
```yaml
# monitoring/docker-compose.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  jaeger:
    image: jaegertracing/all-in-one
    ports:
      - "16686:16686"
      - "14268:14268"
```

## Cost Optimization

### 1. **Intelligent Routing**
- Route simple documents to cheaper models (GPT-4o-mini)
- Route complex documents to premium models (GPT-4o)
- Use confidence scores to determine routing

### 2. **Queue Management**
- Implement priority queues for different document types
- Batch processing for non-urgent requests
- Smart load distribution across workers

### 3. **Batch Processing**
- Group similar documents for batch processing
- Implement smart queuing based on document type
- Use off-peak hours for non-urgent processing

## Implementation Timeline

### Week 1-2: Foundation
- Set up load balancer with 3 instances
- Implement Redis caching
- Add async processing with Celery

### Week 3-4: Multi-Provider
- Integrate multiple LLM providers
- Implement circuit breaker pattern
- Add comprehensive monitoring

### Week 5-6: Kubernetes
- Deploy to Kubernetes cluster
- Set up auto-scaling
- Implement multi-region deployment

### Week 7-8: Optimization
- Fine-tune caching strategies
- Optimize cost routing
- Performance testing and tuning

## Expected Performance

| Tier | Daily Requests | Response Time | Availability | Monthly Cost |
|------|---------------|---------------|--------------|--------------|
| 1    | 100k-300k     | 2-5 seconds   | 99.5%        | $2,000-6,000 |
| 2    | 300k-700k     | 1-3 seconds   | 99.9%        | $6,000-14,000|
| 3    | 700k-1M+      | 0.5-2 seconds | 99.95%       | $14,000-25,000|

This architecture provides a clear path from your current setup to handling 1M+ requests per day while maintaining your 98%+ accuracy and ensuring high availability.
