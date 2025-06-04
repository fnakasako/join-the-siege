# Quick Start Guide

An instance of the app is currently running. 

Test the endpoint:

curl -X POST https://join-the-siege-staging.up.railway.app/classify_file_async -F "file=@files/test.pdf" -F "industry=finance"

##  Run Locally

# Set up environment variables
.env

**Required Environment Variables:**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=sk-your-google-api-key
```

### Start Services
```bash
# Start all services (Redis + API + Worker)
docker-compose up -d

```

App runs at `http://localhost:5000`

### Stop Services
```bash
# Stop all services
docker-compose down

```

# Test classification endpoint (local)
curl -X POST http://localhost:5000/classify_file \
  -F "file=@files/test.pdf" \
  -F "industry=finance"

# Check available industries
curl http://localhost:5000/industries

## Deploy with Railway

We use Railway for quick deployment. Follow the steps below to launch your own instance:

Railway:

After connecting your code repo, add following env variables to Railway deployment: 
OPENAI_API_KEY
GOOGLE_API_KEY
ANTHROPIC_API_KEY

You need to create a redis instance on railway, then create a new REDIS_URL in the code repo's environment variables settings page.

# The final step for Railway is to create a celery worker:

-> create new service
-> unnamed service
-> connect the service to code repo
-> create REDIS_URL environment variable for the service

CI/CD is set up on push to 'main' branch.


## Tests

### Docker Testing (Recommended)

You can run the tests manually using docker:

```bash
# Run all tests in Docker
./run_tests_docker.sh --all
```

# Run specific test types
./run_tests_docker.sh --unit           # Unit tests only
./run_tests_docker.sh --integration    # Integration tests
./run_tests_docker.sh --performance    # Performance tests


## Key Files

- `docker-compose.yml` - Local development services
- `docker-compose.scale.yml` - Production scaling setup
- `Dockerfile` - Container build instructions
- `start_worker.py` - Railway deployment script
- `railway.json` - Railway service configuration
- `src/app.py` - Main Flask application
- `src/async_classifier.py` - Celery task definitions
