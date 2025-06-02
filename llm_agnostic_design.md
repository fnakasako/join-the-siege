# File-Type Agnostic LLM Classification Design

## Proposed Architecture

### 1. **Universal LLM Classification Function**

```python
def classify_with_llm(
    image_data: bytes,
    text_content: str,
    metadata: dict,
    industry_categories: list,
    processing_context: dict = None
) -> dict:
    """
    File-type agnostic LLM classification
    
    Args:
        image_data: Visual representation of document (always provided)
        text_content: Extracted text content (empty string if none)
        metadata: File metadata (size, pages, type, etc.)
        industry_categories: List of possible classifications
        processing_context: Additional context about how document was processed
    
    Returns:
        {
            'classification': str,
            'confidence': float,
            'reasoning': str
        }
    """
    
    # Build universal prompt
    prompt = build_classification_prompt(
        text_content=text_content,
        metadata=metadata,
        categories=industry_categories,
        processing_context=processing_context
    )
    
    # Call LLM with image and text
    response = call_vision_llm(prompt, image_data)
    
    # Parse and validate response
    return parse_llm_response(response, industry_categories)
```

### 2. **File-Type Specific Processors (Data Preparation)**

```python
def classify_pdf(file: FileStorage) -> dict:
    """PDF-specific processing that feeds into universal LLM"""
    
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
    
    # Call universal classifier
    return classify_with_llm(
        image_data=image_data,
        text_content=text_content,
        metadata=metadata,
        industry_categories=get_finance_categories(),  # Or dynamic based on context
        processing_context=processing_context
    )

def classify_excel(file: FileStorage) -> dict:
    """Excel-specific processing that feeds into universal LLM"""
    
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
    
    # Call same universal classifier
    return classify_with_llm(
        image_data=image_data,
        text_content=text_content,
        metadata=metadata,
        industry_categories=get_finance_categories(),
        processing_context=processing_context
    )

def classify_image(file: FileStorage) -> dict:
    """Image-specific processing that feeds into universal LLM"""
    
    # Extract image metadata
    metadata = extract_image_metadata(file)
    
    # Process image content
    image_data = optimize_image_for_llm(file)
    text_content = ocr_extract_text(file)
    
    # Image-specific processing context
    processing_context = {
        'source_type': 'image',
        'image_format': metadata['image_format'],
        'extraction_method': 'ocr',
        'resolution': f"{metadata['image_width']}x{metadata['image_height']}"
    }
    
    # Call same universal classifier
    return classify_with_llm(
        image_data=image_data,
        text_content=text_content,
        metadata=metadata,
        industry_categories=get_finance_categories(),
        processing_context=processing_context
    )
```

### 3. **Universal Prompt Builder**

```python
def build_classification_prompt(
    text_content: str,
    metadata: dict,
    categories: list,
    processing_context: dict = None
) -> str:
    """Build file-type agnostic classification prompt"""
    
    # Base prompt structure
    prompt = f"""
You are a document classification expert. Analyze this document and classify it into one of the provided categories.

DOCUMENT METADATA:
- Filename: {metadata.get('filename', 'unknown')}
- File Type: {metadata.get('file_type', 'unknown')}
- File Size: {metadata.get('file_size', 0)} bytes
- Page/Sheet Count: {metadata.get('page_count', 1)}
"""

    # Add processing context if available
    if processing_context:
        prompt += f"""
PROCESSING CONTEXT:
- Source Type: {processing_context.get('source_type', 'unknown')}
- Extraction Method: {processing_context.get('extraction_method', 'unknown')}
"""
        
        # Add type-specific context
        if processing_context.get('source_type') == 'pdf':
            prompt += f"- Has Text Layer: {processing_context.get('has_text_layer', False)}\n"
        elif processing_context.get('source_type') == 'excel':
            prompt += f"- Sheet Analyzed: {processing_context.get('sheet_analyzed', 'unknown')}\n"
        elif processing_context.get('source_type') == 'image':
            prompt += f"- Resolution: {processing_context.get('resolution', 'unknown')}\n"

    # Add text content if available
    if text_content and text_content.strip():
        prompt += f"""
EXTRACTED TEXT (first 1000 characters):
{text_content[:1000]}
"""
    else:
        prompt += "\nEXTRACTED TEXT: None (image-only analysis)\n"

    # Add categories
    prompt += f"""
CLASSIFICATION CATEGORIES:
{', '.join(categories)}

INSTRUCTIONS:
1. Analyze both the visual content (image) and extracted text
2. Consider the metadata and processing context
3. Choose the most appropriate category
4. Provide your confidence level (0.0 to 1.0)
5. Explain your reasoning

RESPONSE FORMAT:
{{
    "classification": "category_name",
    "confidence": 0.95,
    "reasoning": "Brief explanation of classification decision"
}}
"""
    
    return prompt
```

### 4. **LLM Interface Layer**

```python
import openai
import base64
from typing import Union

def call_vision_llm(prompt: str, image_data: bytes) -> dict:
    """Call LLM with image and text prompt"""
    
    # Convert image to base64 for API
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",  # Or Claude-3, etc.
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent classification
        )
        
        return {
            'success': True,
            'content': response.choices[0].message.content,
            'model': response.model,
            'usage': response.usage
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'content': None
        }

def parse_llm_response(llm_response: dict, valid_categories: list) -> dict:
    """Parse and validate LLM response"""
    
    if not llm_response['success']:
        return {
            'classification': 'processing_error',
            'confidence': 0.0,
            'reasoning': f"LLM call failed: {llm_response['error']}"
        }
    
    try:
        import json
        
        # Try to parse JSON response
        content = llm_response['content']
        
        # Handle cases where LLM wraps JSON in markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        result = json.loads(content.strip())
        
        # Validate classification is in allowed categories
        classification = result.get('classification', 'unknown')
        if classification not in valid_categories:
            # Try to find closest match or default to unknown
            classification = 'unknown'
        
        return {
            'classification': classification,
            'confidence': float(result.get('confidence', 0.0)),
            'reasoning': result.get('reasoning', 'No reasoning provided')
        }
        
    except Exception as e:
        return {
            'classification': 'parsing_error',
            'confidence': 0.0,
            'reasoning': f"Failed to parse LLM response: {str(e)}"
        }
```

### 5. **Industry Category Management**

```python
def get_finance_categories() -> list:
    """Get financial industry document categories"""
    return [
        'invoice',
        'bank_statement', 
        'financial_report',
        'contract',
        'receipt',
        'tax_document',
        'insurance_document',
        'loan_document',
        'unknown'
    ]

def get_legal_categories() -> list:
    """Get legal industry document categories"""
    return [
        'contract',
        'legal_brief',
        'court_filing',
        'patent_document',
        'compliance_document',
        'unknown'
    ]

def get_categories_for_industry(industry: str) -> list:
    """Dynamic category selection based on industry"""
    category_map = {
        'finance': get_finance_categories(),
        'legal': get_legal_categories(),
        'healthcare': get_healthcare_categories(),
        'default': get_finance_categories()  # Default to finance
    }
    
    return category_map.get(industry, category_map['default'])
```

## Benefits of This Design

### ✅ **Advantages:**

1. **Single LLM Interface**: All file types use the same classification logic
2. **Consistent Prompting**: Standardized prompt structure across file types
3. **Easy Testing**: Can test LLM classification separately from file processing
4. **Flexible Categories**: Easy to change categories per industry
5. **Maintainable**: LLM logic centralized, file processing distributed
6. **Extensible**: Adding new file types only requires data preparation

### 🔧 **Implementation in Current Codebase:**

```python
# Updated src/classifier.py
def classify_file(file: FileStorage) -> dict:
    """Main entry point with universal LLM backend"""
    
    file_type = get_file_extension(file.filename).lower()
    
    # Route to appropriate processor
    if file_type == 'pdf':
        return classify_pdf(file)
    elif file_type in ['jpg', 'jpeg', 'png']:
        return classify_image(file)
    elif file_type in ['xls', 'xlsx']:
        return classify_excel(file)
    # ... etc
    
    # All processors call the same classify_with_llm() function
```

This design gives us the best of both worlds: specialized file processing with universal LLM classification.
