# Deployment Guide: Scaling Document Classifier API

This guide walks you through deploying the scaled document classifier API to handle 100k-1M requests per day with high availability.

## Quick Start (Tier 1: 100k-300k requests/day)

### Prerequisites
- Docker and Docker Compose installed
- Multiple OpenAI API keys (recommended: 3-5 keys)
- At least 8GB RAM and 4 CPU cores
- 50GB+ disk space

### 1. Environment Setup

```bash
# Clone and navigate to your project
cd join-the-siege

# Copy environment template
cp .env.example .env

# Edit .env with your actual values
nano .env
```

**Required Environment Variables:**
```bash
# Multiple OpenAI API keys for load distribution
OPENAI_API_KEY_1=sk-your-first-key
OPENAI_API_KEY_2=sk-your-second-key
OPENAI_API_KEY_3=sk-your-third-key

# Secure database password
DB_PASSWORD=your-secure-password-here

# Grafana admin password
GRAFANA_PASSWORD=your-grafana-password
```

### 2. Deploy Scaled Infrastructure

```bash
# Build and start all services
docker-compose -f docker-compose.scale.yml up -d

# Check service health
docker-compose -f docker-compose.scale.yml ps

# View logs
docker-compose -f docker-compose.scale.yml logs -f
```

### 3. Verify Deployment

```bash
# Test load balancer
curl http://localhost/health

# Test classification endpoint
curl -X POST -F "file=@files/invoice_1.pdf" -F "industry=finance" \
  http://localhost/classify_file

# Test async endpoint
curl -X POST -F "file=@files/invoice_1.pdf" -F "industry=finance" \
  http://localhost/classify_file_async

# Check monitoring dashboards
open http://localhost:3000  # Grafana (admin/your-grafana-password)
open http://localhost:9090  # Prometheus
```

## Architecture Overview

### Current Deployment (Tier 1)
```
Internet → Nginx Load Balancer → 3x Flask Instances
                                ↓
                              Redis Cache
                                ↓
                            PostgreSQL DB
                                ↓
                          Celery Workers
```

### Services Deployed:
- **nginx-lb**: Load balancer with rate limiting
- **classifier-1,2,3**: Flask API instances with different OpenAI keys
- **redis**: Message broker for async task queue
- **postgres**: Analytics and metrics storage
- **celery-worker**: Async processing queue
- **celery-beat**: Scheduled tasks (cleanup, metrics)
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards

## API Endpoints

### Synchronous Classification
```bash
POST /classify_file
Content-Type: multipart/form-data

# Form data:
file: [document file]
industry: finance|legal|healthcare (optional, default: finance)

# Response:
{
  "file_class": "invoice",
  "confidence": 0.95,
  "industry": "finance",
  "reasoning": "Document contains invoice-specific elements...",
  "metadata": {...}
}
```

### Asynchronous Classification (Recommended for Scale)
```bash
# Submit for processing
POST /classify_file_async
Content-Type: multipart/form-data

# Response:
{
  "task_id": "abc123-def456",
  "status": "processing",
  "estimated_time": "30-60 seconds",
  "check_url": "/classification_result/abc123-def456"
}

# Check result
GET /classification_result/{task_id}

# Response (when complete):
{
  "status": "completed",
  "result": {
    "file_class": "invoice",
    "confidence": 0.95,
    "processing_time": 45.2,
    "cached": false
  }
}
```

### Health and Monitoring
```bash
GET /health          # Load balancer health check
GET /ready           # Kubernetes readiness check
GET /metrics         # Prometheus metrics
GET /industries      # Available industries
GET /categories/{industry}  # Categories for industry
```

## Performance Optimization

### 1. Queue Management
The system uses Redis queues for async processing:

```bash
# Check queue statistics
curl http://localhost/metrics

# Response includes:
{
  "queue": {
    "queue_length": 12,
    "memory_used": "15MB",
    "redis_connected": true
  }
}
```

### 2. Load Balancing Strategy
Nginx distributes requests using `least_conn` algorithm:
- Requests go to the instance with fewest active connections
- Failed instances are automatically removed for 30 seconds
- Rate limiting: 2 requests/second for uploads, 10 requests/second for API calls

### 3. OpenAI API Key Rotation
Each Flask instance uses a different OpenAI API key:
- Distributes load across multiple API quotas
- Prevents single point of failure
- Automatic failover if one key hits rate limits

## Monitoring and Alerting

### Grafana Dashboards
Access Grafana at `http://localhost:3000` (admin/your-password):

1. **API Performance Dashboard**
   - Request rate and response times
   - Error rates by endpoint
   - Cache hit rates

2. **System Health Dashboard**
   - CPU, memory, disk usage
   - Redis and PostgreSQL health
   - Celery queue depth

3. **Classification Analytics Dashboard**
   - Classification accuracy trends
   - Industry distribution
   - Processing time analysis

### Key Metrics to Monitor
- **Throughput**: Requests per second
- **Latency**: P95 response time < 5 seconds
- **Error Rate**: < 1% for 4xx/5xx responses
- **Queue Depth**: Celery tasks waiting < 100
- **Worker Utilization**: CPU and memory usage per worker

## Scaling to Higher Tiers

### Tier 2: 300k-700k requests/day
```bash
# Scale up instances
docker-compose -f docker-compose.scale.yml up -d --scale classifier-1=2 --scale classifier-2=2 --scale classifier-3=2

# Add more Celery workers
docker-compose -f docker-compose.scale.yml up -d --scale celery-worker=3
```

### Tier 3: 700k-1M+ requests/day
Deploy the multi-LLM provider system:

1. **Add Anthropic/Google API Keys** to `.env`
2. **Deploy LLM Load Balancer** (see `SCALING_ARCHITECTURE.md`)
3. **Implement Circuit Breakers** for provider failover
4. **Add Geographic Load Balancing**

## Troubleshooting

### Common Issues

**1. High Response Times**
```bash
# Check queue depth
curl http://localhost/metrics | grep queue

# Check Celery queue depth
docker exec -it $(docker ps -q -f name=celery-worker) celery -A src.async_classifier.celery_app inspect active

# Scale up workers if queue is backed up
docker-compose -f docker-compose.scale.yml up -d --scale celery-worker=6
```

**2. OpenAI Rate Limits**
```bash
# Check which instance is hitting limits
docker-compose -f docker-compose.scale.yml logs classifier-1 | grep "rate limit"

# Add more API keys or switch to async processing
```

**3. Redis Connection Issues**
```bash
# Check Redis health
docker exec -it $(docker ps -q -f name=redis) redis-cli ping

# Restart Redis if needed
docker-compose -f docker-compose.scale.yml restart redis
```

**4. Database Connection Issues**
```bash
# Check PostgreSQL health
docker exec -it $(docker ps -q -f name=postgres) pg_isready -U classifier

# Check database logs
docker-compose -f docker-compose.scale.yml logs postgres
```

### Performance Tuning

**1. Optimize Cache Settings**
```bash
# Increase cache memory (in docker-compose.scale.yml)
command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
```

**2. Tune Celery Workers**
```bash
# Increase worker concurrency (in docker-compose.scale.yml)
command: celery -A src.async_classifier.celery_app worker --loglevel=info --concurrency=8
```

**3. Optimize Nginx**
```bash
# Increase worker connections (in nginx.conf)
worker_connections 2048;
```

## Security Considerations

### 1. API Key Management
- Store API keys in environment variables only
- Rotate API keys regularly
- Monitor API key usage for anomalies

### 2. Rate Limiting
- Nginx implements IP-based rate limiting
- Adjust limits based on your traffic patterns
- Consider implementing API key-based rate limiting

### 3. Network Security
- Use HTTPS in production (SSL certificates in `/ssl` directory)
- Restrict database access to application containers only
- Implement firewall rules for production deployment

### 4. Data Privacy
- Documents are processed in memory only
- No document content is stored permanently
- Classification results can be stored for analytics (optional)

## Cost Optimization

### Current Costs (Estimated)
- **OpenAI API**: $0.005 per 1K tokens (GPT-4o)
- **Infrastructure**: $200-500/month (3 instances + database + cache)
- **Total**: $2,000-6,000/month for 100k-300k requests/day

### Cost Reduction Strategies
1. **Use GPT-4o-mini** for simple documents (60% cost reduction)
2. **Implement confidence-based routing** (high confidence → cheaper model)
3. **Batch processing** during off-peak hours
4. **Priority queues** for urgent vs. non-urgent requests

## Next Steps

1. **Deploy Tier 1** and monitor performance
2. **Optimize queue management** and worker allocation
3. **Scale horizontally** when approaching capacity limits
4. **Implement Tier 2/3** features as needed

For advanced scaling beyond 1M requests/day, see `SCALING_ARCHITECTURE.md` for Kubernetes deployment and multi-LLM provider strategies.
