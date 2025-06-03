#!/usr/bin/env python3
"""
Comprehensive Test Runner for Document Classification System
Measures: Accuracy, Latency, Availability, and Cost
Designed for CI/CD pipeline integration with Railway
"""

import os
import sys
import time
import json
import asyncio
import statistics
from datetime import datetime
from typing import Dict, List, Any
import requests
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.classifier.file_type_handling.file_type_processors import classify_file
from werkzeug.datastructures import FileStorage
from io import BytesIO

class TestMetrics:
    def __init__(self):
        self.accuracy_tests = []
        self.latency_tests = []
        self.availability_tests = []
        self.cost_tests = []
        self.start_time = time.time()
        
    def add_accuracy_test(self, expected: str, actual: str, confidence: float, test_name: str):
        """Record accuracy test result"""
        correct = expected.lower() == actual.lower()
        self.accuracy_tests.append({
            'test_name': test_name,
            'expected': expected,
            'actual': actual,
            'confidence': confidence,
            'correct': correct,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_latency_test(self, duration: float, test_name: str, provider: str = None):
        """Record latency test result"""
        self.latency_tests.append({
            'test_name': test_name,
            'duration_ms': duration * 1000,
            'provider': provider,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_availability_test(self, success: bool, test_name: str, error: str = None):
        """Record availability test result"""
        self.availability_tests.append({
            'test_name': test_name,
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_cost_test(self, tokens_used: int, estimated_cost: float, provider: str, test_name: str):
        """Record cost test result"""
        self.cost_tests.append({
            'test_name': test_name,
            'tokens_used': tokens_used,
            'estimated_cost_usd': estimated_cost,
            'provider': provider,
            'timestamp': datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_time = time.time() - self.start_time
        
        # Accuracy metrics
        accuracy_rate = 0
        avg_confidence = 0
        if self.accuracy_tests:
            correct_count = sum(1 for test in self.accuracy_tests if test['correct'])
            accuracy_rate = correct_count / len(self.accuracy_tests)
            avg_confidence = statistics.mean(test['confidence'] for test in self.accuracy_tests)
        
        # Latency metrics
        avg_latency = 0
        p95_latency = 0
        if self.latency_tests:
            latencies = [test['duration_ms'] for test in self.latency_tests]
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        
        # Availability metrics
        availability_rate = 0
        if self.availability_tests:
            success_count = sum(1 for test in self.availability_tests if test['success'])
            availability_rate = success_count / len(self.availability_tests)
        
        # Cost metrics
        total_cost = sum(test['estimated_cost_usd'] for test in self.cost_tests)
        total_tokens = sum(test['tokens_used'] for test in self.cost_tests)
        
        return {
            'summary': {
                'total_test_time_seconds': total_time,
                'accuracy_rate': accuracy_rate,
                'average_confidence': avg_confidence,
                'average_latency_ms': avg_latency,
                'p95_latency_ms': p95_latency,
                'availability_rate': availability_rate,
                'total_cost_usd': total_cost,
                'total_tokens_used': total_tokens,
                'tests_run': {
                    'accuracy': len(self.accuracy_tests),
                    'latency': len(self.latency_tests),
                    'availability': len(self.availability_tests),
                    'cost': len(self.cost_tests)
                }
            },
            'detailed_results': {
                'accuracy_tests': self.accuracy_tests,
                'latency_tests': self.latency_tests,
                'availability_tests': self.availability_tests,
                'cost_tests': self.cost_tests
            }
        }

def classify_file_from_path(file_path: str, industry: str = 'finance') -> dict:
    """Helper function to classify a file from its path"""
    try:
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Get filename
        filename = Path(file_path).name
        
        # Create a FileStorage object for the classifier
        file_obj = FileStorage(
            stream=BytesIO(file_data),
            filename=filename,
            content_type='application/pdf' if filename.endswith('.pdf') else 'image/jpeg'
        )
        
        # Classify the document
        result = classify_file(file_obj, industry=industry)
        
        return result
        
    except Exception as e:
        return {
            'classification': 'error',
            'confidence': 0.0,
            'error': str(e)
        }

class DocumentClassificationTester:
    def __init__(self):
        self.metrics = TestMetrics()
        self.test_files_dir = Path("files")
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Test cases with expected classifications
        self.test_cases = [
            {"file": "bank_statement_1.pdf", "expected": "bank_statement"},
            {"file": "bank_statement_2.pdf", "expected": "bank_statement"},
            {"file": "bank_statement_3.pdf", "expected": "bank_statement"},
            {"file": "invoice_1.pdf", "expected": "invoice"},
            {"file": "invoice_2.pdf", "expected": "invoice"},
            {"file": "invoice_3.pdf", "expected": "invoice"},
            {"file": "drivers_license_1.jpg", "expected": "drivers_license"},
            {"file": "drivers_licence_2.jpg", "expected": "drivers_license"},
            {"file": "drivers_license_3.jpg", "expected": "drivers_license"},
        ]
        
    def test_accuracy(self):
        """Test classification accuracy with known test cases"""
        print("🎯 Running Accuracy Tests...")
        
        for test_case in self.test_cases:
            file_path = self.test_files_dir / test_case["file"]
            if not file_path.exists():
                print(f"⚠️  Test file not found: {file_path}")
                continue
                
            try:
                start_time = time.time()
                result = classify_file_from_path(str(file_path))
                duration = time.time() - start_time
                
                # Record accuracy
                self.metrics.add_accuracy_test(
                    expected=test_case["expected"],
                    actual=result.get('classification', 'unknown'),
                    confidence=result.get('confidence', 0.0),
                    test_name=f"accuracy_{test_case['file']}"
                )
                
                # Record latency
                self.metrics.add_latency_test(
                    duration=duration,
                    test_name=f"latency_{test_case['file']}",
                    provider=result.get('provider_used', 'unknown')
                )
                
                # Record availability
                self.metrics.add_availability_test(
                    success=True,
                    test_name=f"availability_{test_case['file']}"
                )
                
                # Record cost (if usage data available)
                if 'usage' in result and result['usage']:
                    usage = result['usage']
                    tokens = usage.get('total_tokens', 0)
                    # Estimate cost based on provider and tokens
                    estimated_cost = self.estimate_cost(tokens, result.get('provider_used', 'openai_gpt4o_mini'))
                    self.metrics.add_cost_test(
                        tokens_used=tokens,
                        estimated_cost=estimated_cost,
                        provider=result.get('provider_used', 'unknown'),
                        test_name=f"cost_{test_case['file']}"
                    )
                
                print(f"✅ {test_case['file']}: {result.get('classification')} (confidence: {result.get('confidence', 0):.2f})")
                
            except Exception as e:
                print(f"❌ {test_case['file']}: Error - {str(e)}")
                self.metrics.add_availability_test(
                    success=False,
                    test_name=f"availability_{test_case['file']}",
                    error=str(e)
                )
    
    def test_api_endpoints(self, base_url: str = "http://localhost:5000"):
        """Test API endpoint availability and performance"""
        print("🌐 Running API Endpoint Tests...")
        
        endpoints = [
            {"path": "/health", "method": "GET"},
            {"path": "/classify", "method": "POST"},
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    response = requests.get(f"{base_url}{endpoint['path']}", timeout=30)
                else:
                    # For POST /classify, we need to send a test file
                    test_file = self.test_files_dir / "invoice_1.pdf"
                    if test_file.exists():
                        with open(test_file, 'rb') as f:
                            files = {'file': f}
                            response = requests.post(f"{base_url}{endpoint['path']}", files=files, timeout=60)
                    else:
                        print(f"⚠️  Test file not found for API test: {test_file}")
                        continue
                
                duration = time.time() - start_time
                
                # Record latency
                self.metrics.add_latency_test(
                    duration=duration,
                    test_name=f"api_{endpoint['method']}_{endpoint['path'].replace('/', '_')}",
                    provider="api"
                )
                
                # Record availability
                success = 200 <= response.status_code < 300
                self.metrics.add_availability_test(
                    success=success,
                    test_name=f"api_{endpoint['method']}_{endpoint['path'].replace('/', '_')}",
                    error=None if success else f"HTTP {response.status_code}"
                )
                
                print(f"✅ {endpoint['method']} {endpoint['path']}: {response.status_code} ({duration*1000:.0f}ms)")
                
            except Exception as e:
                print(f"❌ {endpoint['method']} {endpoint['path']}: Error - {str(e)}")
                self.metrics.add_availability_test(
                    success=False,
                    test_name=f"api_{endpoint['method']}_{endpoint['path'].replace('/', '_')}",
                    error=str(e)
                )
    
    def test_load_performance(self, num_requests: int = 10):
        """Test system performance under load"""
        print(f"⚡ Running Load Performance Tests ({num_requests} requests)...")
        
        test_file = self.test_files_dir / "invoice_1.pdf"
        if not test_file.exists():
            print(f"⚠️  Test file not found: {test_file}")
            return
        
        for i in range(num_requests):
            try:
                start_time = time.time()
                result = classify_file_from_path(str(test_file))
                duration = time.time() - start_time
                
                self.metrics.add_latency_test(
                    duration=duration,
                    test_name=f"load_test_{i+1}",
                    provider=result.get('provider_used', 'unknown')
                )
                
                self.metrics.add_availability_test(
                    success=True,
                    test_name=f"load_test_{i+1}"
                )
                
                print(f"✅ Load test {i+1}/{num_requests}: {duration*1000:.0f}ms")
                
            except Exception as e:
                print(f"❌ Load test {i+1}/{num_requests}: Error - {str(e)}")
                self.metrics.add_availability_test(
                    success=False,
                    test_name=f"load_test_{i+1}",
                    error=str(e)
                )
    
    def estimate_cost(self, tokens: int, provider: str) -> float:
        """Estimate cost based on tokens and provider"""
        # Cost per 1K tokens (approximate)
        cost_per_1k = {
            'openai_gpt4o_mini': 0.0006,  # Average of input/output
            'openai_gpt4o': 0.01,
            'google_gemini': 0.0005,
            'anthropic_claude': 0.008,
        }
        
        rate = cost_per_1k.get(provider, 0.001)  # Default rate
        return (tokens / 1000) * rate
    
    def run_all_tests(self, include_api_tests: bool = False, include_load_tests: bool = False):
        """Run all test suites"""
        print("🚀 Starting Comprehensive Test Suite...")
        print("=" * 60)
        
        # Core functionality tests
        self.test_accuracy()
        
        # API tests (if requested and API is available)
        if include_api_tests:
            self.test_api_endpoints()
        
        # Load tests (if requested)
        if include_load_tests:
            self.test_load_performance()
        
        # Generate and save results
        results = self.metrics.get_summary()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        self.print_summary(results)
        
        # Save summary for CI/CD
        summary_file = self.results_dir / "latest_test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results['summary'], f, indent=2)
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary to console"""
        summary = results['summary']
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"🎯 Accuracy Rate: {summary['accuracy_rate']:.1%}")
        print(f"🔮 Average Confidence: {summary['average_confidence']:.2f}")
        print(f"⚡ Average Latency: {summary['average_latency_ms']:.0f}ms")
        print(f"📈 P95 Latency: {summary['p95_latency_ms']:.0f}ms")
        print(f"🟢 Availability Rate: {summary['availability_rate']:.1%}")
        print(f"💰 Total Cost: ${summary['total_cost_usd']:.4f}")
        print(f"🎫 Total Tokens: {summary['total_tokens_used']:,}")
        print(f"⏱️  Total Test Time: {summary['total_test_time_seconds']:.1f}s")
        print("=" * 60)
        
        # Determine if tests passed
        passed = (
            summary['accuracy_rate'] >= 0.8 and  # 80% accuracy
            summary['average_latency_ms'] <= 10000 and  # 10s max latency
            summary['availability_rate'] >= 0.95  # 95% availability
        )
        
        if passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
            
        print("=" * 60)

def main():
    """Main test runner function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Document Classification Test Runner')
    parser.add_argument('--api-tests', action='store_true', help='Include API endpoint tests')
    parser.add_argument('--load-tests', action='store_true', help='Include load performance tests')
    parser.add_argument('--ci', action='store_true', help='CI mode - exit with error code if tests fail')
    
    args = parser.parse_args()
    
    tester = DocumentClassificationTester()
    results = tester.run_all_tests(
        include_api_tests=args.api_tests,
        include_load_tests=args.load_tests
    )
    
    # Exit with appropriate code for CI/CD
    if args.ci:
        summary = results['summary']
        passed = (
            summary['accuracy_rate'] >= 0.8 and
            summary['average_latency_ms'] <= 10000 and
            summary['availability_rate'] >= 0.95
        )
        sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
