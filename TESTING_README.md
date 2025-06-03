# Testing Guide

This document explains how to run tests for the Document Classification System.

## 🚀 Quick Start

### Running Tests in Docker (Recommended)

The easiest and most reliable way to run tests is using Docker, which ensures all dependencies are available:

```bash
# Run all tests
./run_tests_docker.sh --all

# Run specific test types
./run_tests_docker.sh --unit           # Unit tests only
./run_tests_docker.sh --integration    # Integration tests only
./run_tests_docker.sh --performance    # Performance/accuracy tests only

# Run with coverage
./run_tests_docker.sh --all --coverage
```

### Running Tests Locally

If you have all dependencies installed locally:

```bash
# Run all tests
./run_tests.py --all

# Run specific test types
./run_tests.py --unit           # Unit tests only
./run_tests.py --integration    # Integration tests only
./run_tests.py --performance    # Performance/accuracy tests only

# Run with coverage
./run_tests.py --all --coverage
```

## 📁 Test Structure

```
tests/
├── test_file_type_handlers.py     # Unit tests for file processors
├── test_multi_provider_llm.py     # Unit tests for multi-LLM system
├── test_integration.py            # Integration tests
├── test_app.py                    # Flask app tests
└── test_performance_accuracy.py   # Performance/accuracy tests
```

## 🧪 Test Types

### Unit Tests (`@pytest.mark.unit`)
- Test individual components in isolation
- File type processors (PDF, image, Excel, Word)
- Document utilities (conversion, OCR, optimization)
- Multi-provider LLM logic (backups, upgrades, health monitoring)
- Fast execution, no external dependencies

### Integration Tests (`@pytest.mark.integration`)
- **Mocked Integration Tests**: Test complete workflows with mocked dependencies
- **Real Integration Tests** (`@pytest.mark.requires_api_key`): Test with actual files and API calls
- API endpoints with real Flask app
- File classification pipelines using files from `files/` directory
- Multi-provider system integration
- Error handling and resilience
- System accuracy and performance measurement

### Performance Tests (`@pytest.mark.performance`)
- Measure classification accuracy with real test files
- Track response times (average, P95)
- Monitor system availability
- Estimate costs based on token usage

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery settings
- Markers for different test types
- Output formatting
- Warning suppression

### Test Markers
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - End-to-end tests
- `@pytest.mark.performance` - Performance/accuracy tests
- `@pytest.mark.slow` - Time-intensive tests
- `@pytest.mark.requires_api_key` - Tests needing API keys

## 📊 Test Results

### Coverage Reports
When running with `--coverage`, reports are generated in:
- `htmlcov/index.html` - Interactive HTML coverage report
- Terminal output - Summary coverage statistics

### Performance Results
Performance tests save results in `test_results/`:
- `latest_test_summary.json` - Latest test summary
- `test_results_YYYYMMDD_HHMMSS.json` - Detailed timestamped results

## 🐳 Docker Testing

### Why Use Docker?
- **Consistent Environment**: Same dependencies as production
- **No Local Setup**: No need to install all dependencies locally
- **Isolation**: Tests don't affect your local environment
- **CI/CD Ready**: Same environment used in deployment pipeline

### Docker Test Process
1. Builds the application container
2. Starts Redis for async testing
3. Runs tests with proper environment variables
4. Saves results to `test_results/` directory
5. Displays summary statistics

## 🚨 Troubleshooting

### Common Issues

1. **Missing Dependencies Locally**
   ```
   ModuleNotFoundError: No module named 'openai'
   ```
   **Solution**: Use Docker testing: `./run_tests_docker.sh --unit`

2. **Docker Build Fails**
   ```
   Error: Could not find a version that satisfies the requirement
   ```
   **Solution**: Check `requirements.txt` for version conflicts

3. **API Key Missing**
   ```
   Error: OpenAI client initialization failed
   ```
   **Solution**: Set `OPENAI_API_KEY` environment variable

4. **Redis Connection Error**
   ```
   Error: Redis connection failed
   ```
   **Solution**: Ensure Redis is running in Docker

### Debug Mode

Run tests with verbose output:
```bash
./run_tests_docker.sh --unit --verbose
```

### Checking Logs

View detailed test results:
```bash
cat test_results/latest_test_summary.json | jq '.'
```

## 🎯 Best Practices

### Writing Tests
- Use descriptive test names
- Mock external dependencies
- Test both success and failure cases
- Keep tests independent and isolated

### Running Tests
- Use Docker for consistent results
- Run unit tests frequently during development
- Run integration tests before commits
- Run performance tests before releases

### CI/CD Integration
- All tests run automatically on push/PR
- Performance tests monitor production quality
- Test results are commented on pull requests
- Failed tests block deployments

## 📈 Continuous Monitoring

### Quality Gates
Tests must pass these thresholds:
- **Accuracy**: ≥ 80%
- **Latency**: ≤ 10 seconds
- **Availability**: ≥ 95%

### Performance Tracking
- Response time trends
- Accuracy over time
- Cost per classification
- Provider health status

## 🔗 Related Documentation

- [TESTING_AND_CICD_GUIDE.md](TESTING_AND_CICD_GUIDE.md) - Comprehensive testing guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [SCALING_ARCHITECTURE.md](SCALING_ARCHITECTURE.md) - System architecture
