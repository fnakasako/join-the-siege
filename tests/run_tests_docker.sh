#!/bin/bash
# Script to run tests inside Docker container
# Usage: ./run_tests_docker.sh [--unit] [--integration] [--performance] [--all] [--coverage]

set -e

echo "🐳 Running tests inside Docker container..."

# Load environment variables from .env file
if [ -f ../.env ]; then
    echo "📄 Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source ../.env
    set +a  # stop automatically exporting
else
    echo "⚠️  Warning: .env file not found"
fi

# Change to parent directory for docker operations
cd ..

# Build the container if needed
echo "Building Docker container..."
docker-compose build api

# Create test results directory
mkdir -p test_results

# Run tests inside container
echo "Running comprehensive tests..."
docker-compose run --rm \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -e GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  -e REDIS_URL="redis://redis:6379" \
  -e FLASK_ENV="testing" \
  -v "$(pwd)/test_results:/app/test_results" \
  -v "$(pwd)/files:/app/files" \
  api python tests/run_tests.py "$@"

echo "✅ Tests completed! Results saved in test_results/"

# Display summary if available
if [ -f "test_results/latest_test_summary.json" ]; then
  echo ""
  echo "📊 Quick Summary:"
  python3 -c "
import json
try:
    with open('test_results/latest_test_summary.json', 'r') as f:
        summary = json.load(f)
    print(f\"🎯 Accuracy: {summary['accuracy_rate']:.1%}\")
    print(f\"⚡ Avg Latency: {summary['average_latency_ms']:.0f}ms\")
    print(f\"🟢 Availability: {summary['availability_rate']:.1%}\")
    print(f\"💰 Total Cost: \${summary['total_cost_usd']:.4f}\")
except Exception as e:
    print(f\"Could not read summary: {e}\")
"
fi
