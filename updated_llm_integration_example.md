# Updated LLM Integration with JSON Category Loading

## How to Use the Category System in Your LLM Pipeline

### 1. **Import the Category Loader**

```python
# In your classifier.py or LLM module
from src.classifier.pre_processing import get_categories_for_industry, get_all_industries

# Or import the class directly for more control
from src.classifier.pre_processing import CategoryLoader
```

### 2. **Updated Universal LLM Classification Function**

```python
from werkzeug.datastructures import FileStorage
from src.classifier.pre_processing import get_categories_for_industry

def classify_with_llm(
    image_data: bytes,
    text_content: str,
    metadata: dict,
    industry: str = 'finance',  # Default to finance
    processing_context: dict = None
) -> dict:
    """
    File-type agnostic LLM classification with dynamic category loading
    
    Args:
        image_data: Visual representation of document
        text_content: Extracted text content
        metadata: File metadata
        industry: Industry to get categories for ('finance', 'legal', etc.)
        processing_context: Additional processing context
    
    Returns:
        {
            'classification': str,
            'confidence': float,
            'reasoning': str,
            'industry': str,
            'available_categories': list
        }
    """
    
    # Load categories dynamically from JSON
    industry_categories = get_categories_for_industry(industry)
    
    # Build universal prompt with loaded categories
    prompt = build_classification_prompt(
        text_content=text_content,
        metadata=metadata,
        categories=industry_categories,
        industry=industry,
        processing_context=processing_context
    )
    
    # Call LLM with image and text
    response = call_vision_llm(prompt, image_data)
    
    # Parse and validate response
    result = parse_llm_response(response, industry_categories)
    
    # Add industry context to result
    result['industry'] = industry
    result['available_categories'] = industry_categories
    
    return result
```

### 3. **Updated File-Type Processors**

```python
def classify_pdf(file: FileStorage, industry: str = 'finance') -> dict:
    """PDF-specific processing with dynamic industry categories"""
    
    # Extract PDF metadata
    metadata = extract_pdf_metadata(file)
    
    # Process PDF content
    image_data = pdf_to_image(file, page=0)
    text_content = extract_pdf_text(file, page=0)
    
    # PDF-specific processing context
    processing_context = {
        'source_type': 'pdf',
        'has_text_layer': metadata['has_text'],
        'extraction_method': 'pdf_conversion',
        'page_analyzed': 1
    }
    
    # Call universal classifier with industry parameter
    return classify_with_llm(
        image_data=image_data,
        text_content=text_content,
        metadata=metadata,
        industry=industry,  # Dynamic industry selection
        processing_context=processing_context
    )

def classify_excel(file: FileStorage, industry: str = 'finance') -> dict:
    """Excel-specific processing with dynamic industry categories"""
    
    # Extract Excel metadata
    metadata = extract_excel_metadata(file)
    
    # Process Excel content
    image_data = excel_to_image(file, sheet=0)
    text_content = extract_excel_text(file, sheet=0)
    
    # Excel-specific processing context
    processing_context = {
        'source_type': 'excel',
        'sheet_count': metadata['sheet_count'],
        'extraction_method': 'excel_conversion',
        'sheet_analyzed': metadata['sheet_names'][0] if metadata['sheet_names'] else 'Sheet1'
    }
    
    # Call universal classifier with industry parameter
    return classify_with_llm(
        image_data=image_data,
        text_content=text_content,
        metadata=metadata,
        industry=industry,  # Dynamic industry selection
        processing_context=processing_context
    )
```

### 4. **Updated Main Classifier with Industry Support**

```python
# Updated src/classifier.py
from werkzeug.datastructures import FileStorage
from src.classifier.pre_processing import get_categories_for_industry, get_all_industries

def classify_file(file: FileStorage, industry: str = 'finance') -> dict:
    """
    Main entry point with industry-specific category support
    
    Args:
        file: FileStorage object to classify
        industry: Industry context ('finance', 'legal', 'healthcare', etc.)
    
    Returns:
        Classification result with industry-specific categories
    """
    
    file_type = get_file_extension(file.filename).lower()
    
    # Route to appropriate processor with industry parameter
    if file_type == 'pdf':
        return classify_pdf(file, industry=industry)
    elif file_type in ['jpg', 'jpeg', 'png']:
        return classify_image(file, industry=industry)
    elif file_type in ['xls', 'xlsx']:
        return classify_excel(file, industry=industry)
    elif file_type in ['doc', 'docx']:
        return classify_word(file, industry=industry)
    elif file_type in ['ppt', 'pptx']:
        return classify_powerpoint(file, industry=industry)
    elif file_type in ['txt', 'csv']:
        return classify_text(file, industry=industry)
    else:
        return {
            'classification': 'unknown_file_type',
            'confidence': 0.0,
            'industry': industry,
            'available_categories': get_categories_for_industry(industry)
        }
```

### 5. **Updated Flask App with Industry Parameter**

```python
# Updated src/app.py
from flask import Flask, request, jsonify
from src.classifier import classify_file
from src.classifier.pre_processing import get_all_industries

app = Flask(__name__)

@app.route('/classify_file', methods=['POST'])
def classify_file_route():
    """Enhanced endpoint with industry parameter support"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    # Get industry parameter from request (default to 'finance')
    industry = request.form.get('industry', 'finance').lower()
    
    # Validate industry
    available_industries = get_all_industries()
    if industry not in available_industries and industry != 'default':
        return jsonify({
            "error": f"Invalid industry. Available: {available_industries}"
        }), 400

    # Classify with industry context
    result = classify_file(file, industry=industry)
    
    return jsonify({
        "file_class": result['classification'],
        "confidence": result['confidence'],
        "industry": result['industry'],
        "available_categories": result['available_categories'],
        "reasoning": result.get('reasoning', ''),
        "metadata": result.get('metadata', {})
    }), 200

@app.route('/industries', methods=['GET'])
def get_industries():
    """Endpoint to get available industries"""
    return jsonify({
        "industries": get_all_industries()
    }), 200

@app.route('/categories/<industry>', methods=['GET'])
def get_categories(industry):
    """Endpoint to get categories for a specific industry"""
    try:
        categories = get_categories_for_industry(industry)
        return jsonify({
            "industry": industry,
            "categories": categories
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

### 6. **Usage Examples**

```bash
# Classify with default finance categories
curl -X POST -F 'file=@invoice.pdf' http://127.0.0.1:5000/classify_file

# Classify with legal categories
curl -X POST -F 'file=@contract.pdf' -F 'industry=legal' http://127.0.0.1:5000/classify_file

# Classify with healthcare categories
curl -X POST -F 'file=@medical_record.pdf' -F 'industry=healthcare' http://127.0.0.1:5000/classify_file

# Get available industries
curl http://127.0.0.1:5000/industries

# Get categories for specific industry
curl http://127.0.0.1:5000/categories/legal
```

### 7. **Testing the Category System**

```python
# Test script to verify category loading
from src.classifier.pre_processing import get_categories_for_industry, get_all_industries

def test_category_system():
    """Test the category loading system"""
    
    print("Available industries:")
    industries = get_all_industries()
    for industry in industries:
        print(f"  - {industry}")
    
    print("\nTesting category loading:")
    for industry in ['finance', 'legal', 'healthcare']:
        categories = get_categories_for_industry(industry)
        print(f"{industry}: {len(categories)} categories")
        print(f"  Sample: {categories[:3]}...")
    
    print("\nTesting unknown industry:")
    unknown_categories = get_categories_for_industry('unknown_industry')
    print(f"Unknown industry gets default: {unknown_categories}")

if __name__ == "__main__":
    test_category_system()
```

## Benefits of This Approach

### ✅ **Advantages:**

1. **Externalized Configuration**: Categories stored in JSON, easy to modify without code changes
2. **Dynamic Loading**: Categories loaded at runtime, supports hot-reloading
3. **Industry Flexibility**: Easy to add new industries and categories
4. **API Support**: REST endpoints to query available industries and categories
5. **Validation**: Built-in validation to ensure categories are valid
6. **Fallback Handling**: Graceful fallback to default categories for unknown industries
7. **Maintainable**: Clear separation between configuration and code

### 🔧 **Easy Maintenance:**

- **Add new industry**: Just add to `industry_categories.json`
- **Modify categories**: Edit JSON file, no code changes needed
- **Deploy updates**: JSON file can be updated independently
- **A/B testing**: Easy to test different category sets

This design gives you complete flexibility to manage document categories externally while maintaining a clean, testable codebase.
