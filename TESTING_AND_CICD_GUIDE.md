# Testing and CI/CD Guide

This guide explains how to run tests and use the CI/CD pipeline for the Document Classification System.

## 🧪 Testing Framework

The testing framework measures four key metrics:
- **Accuracy**: Classification correctness
- **Latency**: Response time performance
- **Availability**: System uptime and reliability
- **Cost**: Token usage and estimated costs

## 🚀 Quick Start

### Running Tests Locally in Docker

The easiest way to run tests is using the Docker container:

```bash
# Basic accuracy tests
./run_tests_docker.sh

# Include API endpoint tests
./run_tests_docker.sh --api-tests

# Include load performance tests
./run_tests_docker.sh --load-tests

# CI mode (exits with error code if tests fail)
./run_tests_docker.sh --ci
```

### Running Tests Directly (if dependencies installed locally)

```bash
# Basic tests
python test_runner.py

# With all test types
python test_runner.py --api-tests --load-tests --ci
```

## 📊 Test Results

Test results are saved in the `test_results/` directory:
- `test_results/latest_test_summary.json` - Latest test summary
- `test_results/test_results_YYYYMMDD_HHMMSS.json` - Detailed timestamped results

### Sample Test Output

```
🚀 Starting Comprehensive Test Suite...
============================================================
🎯 Running Accuracy Tests...
✅ bank_statement_1.pdf: bank_statement (confidence: 0.95)
✅ invoice_1.pdf: invoice (confidence: 0.92)
...

============================================================
📊 TEST SUMMARY
============================================================
🎯 Accuracy Rate: 89.0%
🔮 Average Confidence: 0.91
⚡ Average Latency: 2847ms
📈 P95 Latency: 4200ms
🟢 Availability Rate: 100.0%
💰 Total Cost: $0.0234
🎫 Total Tokens: 15,678
⏱️  Total Test Time: 45.2s
============================================================
✅ ALL TESTS PASSED
============================================================
```

## 🔄 CI/CD Pipeline

The CI/CD pipeline is configured with GitHub Actions and Railway deployment.

### Pipeline Stages

1. **Test** - Run comprehensive tests
2. **Security Scan** - Check for vulnerabilities
3. **Docker Build** - Build and test Docker image
4. **Deploy Staging** - Deploy to staging environment (develop branch)
5. **Deploy Production** - Deploy to production (main branch)
6. **Performance Monitoring** - Monitor production performance

### Branch Strategy

- `main` - Production deployments
- `develop` - Staging deployments
- Feature branches - Run tests only

### Required Secrets

Configure these secrets in your GitHub repository:

```
OPENAI_API_KEY          # OpenAI API key
RAILWAY_TOKEN           # Railway deployment token
STAGING_URL             # Staging environment URL
PRODUCTION_URL          # Production environment URL
```

### Railway Configuration

The `railway.json` file configures Railway deployment:

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "gunicorn -w 2 -b 0.0.0.0:$PORT src.app:app",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

## 🎯 Test Quality Gates

Tests must pass these thresholds:

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Accuracy | ≥ 80% | Ensure classification quality |
| Latency | ≤ 10s | Maintain user experience |
| Availability | ≥ 95% | Ensure system reliability |

## 📈 Performance Monitoring

### Continuous Monitoring

The pipeline includes performance monitoring that:
- Runs after production deployments
- Tests API endpoints under load
- Tracks performance trends over time
- Alerts on performance degradation

### Metrics Tracked

- **Response Time**: P50, P95, P99 latencies
- **Throughput**: Requests per second
- **Error Rate**: Failed requests percentage
- **Cost Efficiency**: Cost per successful classification

## 🛠️ Local Development Testing

### Setting Up Local Environment

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export REDIS_URL="redis://localhost:6379"
   ```

3. **Start Redis** (if testing async features):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

### Running Specific Test Types

```bash
# Test accuracy only
python test_runner.py

# Test API endpoints (requires running server)
python test_runner.py --api-tests

# Load testing
python test_runner.py --load-tests

# All tests with CI exit codes
python test_runner.py --api-tests --load-tests --ci
```

## 🔧 Customizing Tests

### Adding New Test Cases

Edit `test_runner.py` and add to the `test_cases` list:

```python
self.test_cases = [
    {"file": "new_document.pdf", "expected": "expected_category"},
    # ... existing test cases
]
```

### Adjusting Quality Gates

Modify the thresholds in `test_runner.py`:

```python
passed = (
    summary['accuracy_rate'] >= 0.8 and      # 80% accuracy
    summary['average_latency_ms'] <= 10000 and  # 10s max latency
    summary['availability_rate'] >= 0.95     # 95% availability
)
```

### Custom Test Environments

Create environment-specific test configurations:

```bash
# Development environment
FLASK_ENV=development python test_runner.py

# Staging environment
FLASK_ENV=staging python test_runner.py --api-tests

# Production environment
FLASK_ENV=production python test_runner.py --load-tests
```

## 🚨 Troubleshooting

### Common Issues

1. **Missing API Key**:
   ```
   Error: OpenAI client initialization failed
   ```
   Solution: Set `OPENAI_API_KEY` environment variable

2. **Docker Build Fails**:
   ```
   Error: Could not find a version that satisfies the requirement
   ```
   Solution: Check `requirements.txt` for version conflicts

3. **Test Files Not Found**:
   ```
   ⚠️ Test file not found: files/test_document.pdf
   ```
   Solution: Ensure test files exist in the `files/` directory

4. **Redis Connection Error**:
   ```
   Error: Redis connection failed
   ```
   Solution: Start Redis or check `REDIS_URL` configuration

### Debug Mode

Run tests with verbose output:

```bash
PYTHONPATH=/app python -v test_runner.py
```

### Checking Logs

View detailed logs in test results:

```bash
cat test_results/latest_test_summary.json | jq '.'
```

## 📚 Best Practices

### Test Data Management

- Keep test files small (< 1MB) for faster tests
- Use representative documents for each category
- Regularly update test cases with real-world examples

### Performance Optimization

- Run load tests in staging before production
- Monitor token usage to control costs
- Use caching for repeated classifications

### Security

- Never commit API keys to version control
- Use environment variables for sensitive data
- Regularly update dependencies for security patches

### Monitoring

- Set up alerts for test failures
- Track performance trends over time
- Monitor cost increases

## 🔗 Integration with Railway

### Automatic Deployments

- Push to `develop` → Deploy to staging
- Push to `main` → Deploy to production
- Pull requests → Run tests only

### Environment Variables

Set these in Railway dashboard:
- `OPENAI_API_KEY`
- `REDIS_URL` (automatically provided)
- `FLASK_ENV=production`

### Scaling

Railway automatically scales based on traffic. Monitor performance and adjust:
- Worker count in `railway.json`
- Resource limits
- Auto-scaling policies

## 📞 Support

For issues with:
- **Testing Framework**: Check test logs and error messages
- **CI/CD Pipeline**: Review GitHub Actions logs
- **Railway Deployment**: Check Railway dashboard logs
- **Performance Issues**: Review performance monitoring results

Remember to check the test results directory for detailed information about any failures or performance issues.
