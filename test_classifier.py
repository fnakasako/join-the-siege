#!/usr/bin/env python3
"""
Comprehensive test script for multi-provider LLM classifier

Prerequisites:
1. Redis running: docker run -d -p 6379:6379 redis:alpine
2. Celery worker running: celery -A src.async_classifier.celery_app worker --loglevel=info
3. Your .env file with API keys set:
   - OPENAI_API_KEY (required)
   - OPENAI_GPT4O_API_KEY (optional, for quality upgrades)
   - GOOGLE_API_KEY (optional, for backup)
   - ANTHROPIC_API_KEY (optional, for backup)
"""

import time
import requests
import asyncio
from src.async_classifier import (
    submit_classification_task,
    get_task_result
)
from src.multi_provider_llm import multi_provider_llm

def test_multi_provider_llm():
    """Test the multi-provider LLM system directly"""
    
    print("🤖 Testing Multi-Provider LLM System")
    print("=" * 50)
    
    # Test with sample image data (create a simple test image)
    test_image_data = create_test_image_data()
    
    # Test prompt
    prompt = """
You are a document classification expert. Analyze this document and classify it.

CLASSIFICATION CATEGORIES:
bank_statement, invoice, drivers_license, unknown

INSTRUCTIONS:
1. Analyze the visual content
2. Choose the most appropriate category
3. Provide confidence level (0.0 to 1.0)

RESPONSE FORMAT (JSON only):
{
    "classification": "category_name",
    "confidence": 0.95
}
"""
    
    async def run_test():
        try:
            print("\n1. Testing primary provider (GPT-4o-mini)...")
            result = await multi_provider_llm.classify_with_confidence_upgrade(
                prompt, 
                test_image_data, 
                confidence_threshold=0.8
            )
            
            print(f"✅ Classification successful!")
            print(f"   Classification: {result.get('classification', 'unknown')}")
            print(f"   Confidence: {result.get('confidence', 0.0):.2f}")
            print(f"   Provider used: {result.get('provider_used', 'unknown')}")
            print(f"   Model: {result.get('model', 'unknown')}")
            print(f"   Upgraded: {result.get('upgraded', False)}")
            print(f"   Is backup: {result.get('is_backup', False)}")
            
            if result.get('upgraded'):
                print(f"   Original confidence: {result.get('original_confidence', 'N/A')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Multi-provider LLM test failed: {e}")
            return None
    
    # Run the async test
    result = asyncio.run(run_test())
    return result

def test_provider_health():
    """Test provider health monitoring"""
    
    print("\n🏥 Testing Provider Health Monitoring")
    print("=" * 50)
    
    print("\nCurrent provider health status:")
    for provider, health in multi_provider_llm.provider_health.items():
        status = "🟢 Healthy" if multi_provider_llm.is_provider_healthy(provider) else "🔴 Unhealthy"
        print(f"   {provider.value}: {status} (failures: {health['failures']})")
    
    print("\nEnabled backup providers:")
    for provider, config in multi_provider_llm.backup_providers.items():
        status = "🟢 Enabled" if config['enabled'] else "🔴 Disabled"
        print(f"   {provider.value}: {status}")

def test_confidence_upgrade():
    """Test confidence-based quality upgrade"""
    
    print("\n⬆️ Testing Confidence-Based Quality Upgrade")
    print("=" * 50)
    
    # Create a more complex prompt that might result in lower confidence
    complex_prompt = """
Analyze this complex document with multiple potential classifications.

CLASSIFICATION CATEGORIES:
bank_statement, invoice, drivers_license, passport, utility_bill, tax_document, insurance_form, unknown

This document might be ambiguous or contain elements from multiple categories.
Provide your best classification with honest confidence assessment.

RESPONSE FORMAT (JSON only):
{
    "classification": "category_name",
    "confidence": 0.65
}
"""
    
    test_image_data = create_test_image_data()
    
    async def run_upgrade_test():
        try:
            print("\nTesting with lower confidence threshold (0.9) to trigger upgrade...")
            result = await multi_provider_llm.classify_with_confidence_upgrade(
                complex_prompt, 
                test_image_data, 
                confidence_threshold=0.9  # High threshold to likely trigger upgrade
            )
            
            print(f"✅ Upgrade test completed!")
            print(f"   Final classification: {result.get('classification', 'unknown')}")
            print(f"   Final confidence: {result.get('confidence', 0.0):.2f}")
            print(f"   Provider used: {result.get('provider_used', 'unknown')}")
            print(f"   Was upgraded: {result.get('upgraded', False)}")
            
            if result.get('upgraded'):
                print(f"   ⬆️ Quality upgrade triggered!")
                print(f"   Original confidence: {result.get('original_confidence', 'N/A'):.2f}")
            else:
                print(f"   ➡️ No upgrade needed (confidence above threshold)")
            
            return result
            
        except Exception as e:
            print(f"❌ Confidence upgrade test failed: {e}")
            return None
    
    result = asyncio.run(run_upgrade_test())
    return result

def create_test_image_data():
    """Create simple test image data for testing"""
    try:
        # Try to use a real test file if available
        with open('files/invoice_1.pdf', 'rb') as f:
            # For testing, we'll use the PDF bytes directly
            # In real usage, this would be converted to image bytes
            return f.read()[:1000]  # Use first 1KB as test data
    except FileNotFoundError:
        # Create dummy image-like data
        return b"\x89PNG\r\n\x1a\n" + b"dummy image data for testing" * 10

def test_async_classifier():
    """Test the async classifier with a sample file"""
    
    print("🔍 Testing Async Classifier")
    print("=" * 50)
    
    
    # 1. Test with a sample file
    print("\n2. Submitting classification task...")
    
    # Read a test file
    try:
        with open('files/invoice_1.pdf', 'rb') as f:
            file_data = f.read()
        filename = 'invoice_1.pdf'
    except FileNotFoundError:
        print("   No test file found. Creating dummy data...")
        file_data = b"dummy pdf content for testing"
        filename = 'test.pdf'
    
    # Submit task
    task_id = submit_classification_task(file_data, filename, 'finance')
    print(f"   Task submitted: {task_id}")
    
    # 2. Poll for results
    print("\n3. Waiting for results...")
    max_wait = 120  # 2 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        result = get_task_result(task_id)
        status = result['status']
        
        print(f"   Status: {status}")
        
        if status == 'completed':
            print("✅ Classification completed!")
            classification_result = result['result']
            print(f"   Classification: {classification_result.get('classification', 'unknown')}")
            print(f"   Confidence: {classification_result.get('confidence', 0.0)}")
            print(f"   Processing time: {classification_result.get('processing_time', 0.0):.2f}s")
            return
        elif status == 'failed':
            print("❌ Classification failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return
        else:
            print(f"   Still processing... (state: {result.get('state', 'unknown')})")
            time.sleep(5)
    
    print("⏰ Timeout waiting for results")

def test_flask_async_endpoint():
    """Test the Flask async endpoint (if running)"""
    
    print("\n🌐 Testing Flask Async Endpoint")
    print("=" * 50)
    
    # Check if Flask app is running
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        print(f"Flask app status: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Flask app not running on localhost:5000")
        print("   Start with: python src/app.py")
        return
    
    # Test async endpoint
    try:
        with open('files/invoice_1.pdf', 'rb') as f:
            files = {'file': f}
            data = {'industry': 'finance'}
            
            print("Submitting file to /classify_file_async...")
            response = requests.post(
                'http://localhost:5000/classify_file_async',
                files=files,
                data=data,
                timeout=10
            )
            
            if response.status_code == 202:
                result = response.json()
                task_id = result['task_id']
                print(f"✅ Task submitted: {task_id}")
                
                # Poll for results
                print("Polling for results...")
                for i in range(24):  # 2 minutes max
                    time.sleep(5)
                    check_response = requests.get(f'http://localhost:5000/classification_result/{task_id}')
                    check_result = check_response.json()
                    
                    print(f"   Status: {check_result['status']}")
                    
                    if check_result['status'] == 'completed':
                        print("✅ Classification completed via Flask!")
                        classification = check_result['result']
                        print(f"   Classification: {classification.get('classification', 'unknown')}")
                        print(f"   Confidence: {classification.get('confidence', 0.0)}")
                        return
                    elif check_result['status'] == 'failed':
                        print("❌ Classification failed!")
                        print(f"   Error: {check_result.get('error', 'Unknown error')}")
                        return
                
                print("⏰ Timeout waiting for Flask results")
            else:
                print(f"❌ Failed to submit task: {response.status_code}")
                print(f"   Response: {response.text}")
                
    except FileNotFoundError:
        print("❌ No test file found at files/invoice_1.pdf")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🧪 Multi-Provider LLM Classifier Test Suite")
    print("=" * 50)
    
    # Test 1: Multi-provider LLM system
    multi_result = test_multi_provider_llm()
    
    # Test 2: Provider health monitoring
    test_provider_health()
    
    # Test 3: Confidence-based quality upgrade
    upgrade_result = test_confidence_upgrade()
    
    # Test 4: Direct async classifier (existing functionality)
    test_async_classifier()
    
    # Test 5: Flask endpoint (optional)
    test_flask_async_endpoint()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    
    if multi_result:
        print(f"✅ Multi-provider LLM: {multi_result.get('provider_used', 'unknown')}")
    else:
        print("❌ Multi-provider LLM: Failed")
    
    if upgrade_result:
        upgrade_status = "Upgraded" if upgrade_result.get('upgraded') else "No upgrade needed"
        print(f"✅ Quality upgrade: {upgrade_status}")
    else:
        print("❌ Quality upgrade: Failed")
    
    print("\n✨ Testing complete!")
    print("\n💡 Tips:")
    print("   - Add GOOGLE_API_KEY and ANTHROPIC_API_KEY to .env for full redundancy")
    print("   - Monitor provider health in production")
    print("   - Adjust confidence threshold based on your quality requirements")
