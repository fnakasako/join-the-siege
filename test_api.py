#!/usr/bin/env python3
"""
Test script for the document classification API

This script tests the API with the sample files in the 'files' directory.
Make sure to set your OpenAI API key before running.
"""

import requests
import os
from pathlib import Path

# API configuration
API_BASE_URL = "http://127.0.0.1:5000"
FILES_DIR = Path("files")

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/industries")
        if response.status_code == 200:
            print("✅ API is running!")
            print(f"Available industries: {response.json()['industries']}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the Flask app is running.")
        print("Run: python -m src.app")
        return False

def test_file_classification(file_path, industry='finance'):
    """Test classification of a single file"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'industry': industry}
            
            print(f"\n📄 Testing: {file_path.name}")
            response = requests.post(
                f"{API_BASE_URL}/classify_file",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Classification: {result['file_class']}")
                print(f"   Confidence: {result['confidence']:.2f}")
                print(f"   Industry: {result['industry']}")
                if result.get('reasoning'):
                    print(f"   Reasoning: {result['reasoning'][:100]}...")
                return result
            else:
                print(f"❌ Classification failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error testing {file_path.name}: {str(e)}")
        return None

def test_all_files():
    """Test classification of all files in the files directory"""
    if not FILES_DIR.exists():
        print(f"❌ Files directory '{FILES_DIR}' not found")
        return
    
    # Get all files
    test_files = list(FILES_DIR.glob("*"))
    if not test_files:
        print(f"❌ No files found in '{FILES_DIR}'")
        return
    
    print(f"\n🧪 Testing {len(test_files)} files...")
    
    results = []
    for file_path in sorted(test_files):
        if file_path.is_file():
            result = test_file_classification(file_path)
            if result:
                results.append({
                    'filename': file_path.name,
                    'classification': result['file_class'],
                    'confidence': result['confidence']
                })
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"Files tested: {len(results)}")
    
    if results:
        print("\nResults:")
        for result in results:
            print(f"  {result['filename']:<25} → {result['classification']:<15} ({result['confidence']:.2f})")
        
        # Accuracy check (basic)
        correct = 0
        for result in results:
            filename = result['filename'].lower()
            classification = result['classification']
            
            if ('bank_statement' in filename and 'bank_statement' in classification) or \
               ('invoice' in filename and 'invoice' in classification) or \
               ('drivers_license' in filename and 'drivers_license' in classification):
                correct += 1
        
        accuracy = correct / len(results) * 100
        print(f"\n🎯 Basic accuracy: {accuracy:.1f}% ({correct}/{len(results)})")

def test_different_industries():
    """Test the same file with different industries"""
    test_file = FILES_DIR / "invoice_1.pdf"
    if not test_file.exists():
        print("❌ invoice_1.pdf not found for industry testing")
        return
    
    print(f"\n🏭 Testing {test_file.name} with different industries:")
    
    industries = ['finance', 'legal', 'healthcare']
    for industry in industries:
        result = test_file_classification(test_file, industry)
        if result:
            print(f"   {industry}: {result['file_class']} ({result['confidence']:.2f})")

def main():
    """Main test function"""
    print("🚀 Document Classification API Test")
    print("=" * 50)
    
    # Check if API is running
    if not test_api_health():
        return
    
    # Test all files
    test_all_files()
    
    # Test different industries
    test_different_industries()
    
    print(f"\n✨ Testing complete!")
    print("\nTo run the API manually:")
    print("1. Set OpenAI API key: export OPENAI_API_KEY='your-key-here'")
    print("2. Start API: python -m src.app")
    print("3. Test single file: curl -X POST -F 'file=@files/invoice_1.pdf' http://127.0.0.1:5000/classify_file")

if __name__ == "__main__":
    main()
