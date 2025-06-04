# Quick Start Guide

An instance of the app is currently running. 

Test the endpoint:

curl -X POST https://join-the-siege-staging.up.railway.app/classify_file -F "file=@files/test.pdf" -F "industry=finance"

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
docker-compose up -build

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

cd tests

# Run specific test types
./run_tests_docker.sh --unit           # Unit tests only
./run_tests_docker.sh --integration    # Integration tests


## Key Files

### Infrastructure & Deployment
- `docker-compose.yml` - Local development services (Redis + API + Worker)
- `docker-compose.scale.yml` - Production scaling setup with load balancing
- `Dockerfile` - Container build instructions for the application
- `start_worker.py` - Railway deployment script for Celery workers
- `railway.json` - Railway service configuration and deployment settings

### Source Code Structure (`src/`)

The `src/` directory contains the core application code, organized in a modular architecture that separates concerns for maintainability and scalability:

### app.py
- `src/app.py` - **Main Flask application** with REST API endpoints:
  - `/classify_file` - Document classification endpoint with async processing
  - `/industries` - Returns available industry categories
  - `/categories/<industry>` - Returns document categories for specific industry

#### `src/classifier/` 

**Core Classification Logic:**
- `src/classifier/async_classifier.py` - **Celery task definitions** for background processing:
  - Handles async document classification tasks
  - Manages task queuing, execution, and result retrieval
  - Provides fault tolerance and retry mechanisms

**LLM Integration:**
- `src/classifier/llm_call.py` - Core LLM API integration and prompt management
- `src/classifier/multi_provider_llm.py` - **Multi-provider failover system**:
  - Implements hierarchical LLM provider fallback (GPT-4o-mini → GPT-4o → Claude → Gemini)
  - Handles rate limiting, error handling, and automatic provider switching
  - Manages API key rotation and cost optimization

**`src/classifier/categories/`:**
- `src/classifier/categories/category_loader.py` - **Dynamic category loading and validation**:
  - Loads industry-specific document categories from JSON configuration
  - Provides category validation and industry lookup functions
  - Enables easy addition of new industries without code changes
- `src/classifier/categories/industry_categories.json` - **Industry configuration file**:
  - Defines document categories for each supported industry (finance, insurance, legal, etc.)
  - Structured as `{industry: [categories]}` for easy LLM prompt formatting
  - Central configuration point for expanding to new industries

**File Processing Pipeline (`src/classifier/file_type_handling/`):**
- `src/classifier/file_type_handling/file_type_processors.py` - **Multi-format document processors**:
  - PDF text extraction and image processing
  - Word document (.doc/.docx) text extraction
  - Excel spreadsheet (.xls/.xlsx) content processing
  - Image file handling (PNG, JPG, etc.) with OCR capabilities
- `src/classifier/file_type_handling/document_utils.py` - **Document preprocessing utilities**:
  - Text cleaning and normalization
  - Image preprocessing for vision models
  - Content validation and error handling

```
