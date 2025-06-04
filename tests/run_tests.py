#!/usr/bin/env python3
"""
Test runner script for the document classification system
Supports running different types of tests: unit, integration, performance
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError as e:
        print(f"❌ {description} failed: Command not found")
        print("💡 Hint: Try running tests in Docker instead: ./run_tests_docker.sh --unit")
        return False
    except ModuleNotFoundError as e:
        print(f"❌ {description} failed: Missing dependencies")
        print("💡 Hint: Try running tests in Docker instead: ./run_tests_docker.sh --unit")
        return False


def main():
    parser = argparse.ArgumentParser(description='Run tests for document classification system')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--performance', action='store_true', help='Run performance/accuracy tests')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    
    args = parser.parse_args()
    
    # If no specific test type is specified, run all
    if not any([args.unit, args.integration, args.performance]):
        args.all = True
    
    success = True
    
    print("🧪 Document Classification System Test Runner")
    print("=" * 60)
    
    # Base pytest command
    pytest_cmd = ['python', '-m', 'pytest']
    
    if args.verbose:
        pytest_cmd.append('-v')
    
    if args.fast:
        pytest_cmd.extend(['-m', 'not slow'])
    
    if args.coverage:
        pytest_cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term'])
    
    # Run unit tests
    if args.unit or args.all:
        cmd = pytest_cmd + ['-m', 'unit', 'tests/test_file_type_handlers.py', 'tests/test_multi_provider_llm.py']
        if not run_command(cmd, "Running Unit Tests"):
            success = False
    
    # Run integration tests
    if args.integration or args.all:
        cmd = pytest_cmd + ['-m', 'integration', 'tests/test_integration.py', 'tests/test_app.py']
        if not run_command(cmd, "Running Integration Tests"):
            success = False
    
    # Run performance/accuracy tests
    if args.performance or args.all:
        cmd = ['python', 'tests/test_performance_accuracy.py']
        if args.fast:
            cmd.append('--ci')  # Run in CI mode for faster execution
        if not run_command(cmd, "Running Performance/Accuracy Tests"):
            success = False
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
