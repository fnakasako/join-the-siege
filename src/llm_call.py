from openai import OpenAI
import base64
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv
from src.classifier.categories.category_loader import get_categories_for_industry

# Load environment variables from .env file
load_dotenv()

# Model configuration - can be overridden via environment variable
DEFAULT_MODEL = "gpt-4o"
MODEL = os.getenv('OPENAI_MODEL', DEFAULT_MODEL)

# Model cost and capability information (approximate costs per 1K tokens)
MODEL_INFO = {
    "gpt-4o": {"cost_input": 0.005, "cost_output": 0.015, "vision": True, "quality": "highest"},
    "gpt-4o-mini": {"cost_input": 0.00015, "cost_output": 0.0006, "vision": True, "quality": "high"},
    "gpt-4-turbo": {"cost_input": 0.01, "cost_output": 0.03, "vision": True, "quality": "highest"},
    "gpt-3.5-turbo": {"cost_input": 0.0005, "cost_output": 0.0015, "vision": False, "quality": "medium"}
}

print(f"Using model: {MODEL}")
if MODEL in MODEL_INFO:
    info = MODEL_INFO[MODEL]
    print(f"Model info - Input: ${info['cost_input']}/1K tokens, Output: ${info['cost_output']}/1K tokens, Vision: {info['vision']}, Quality: {info['quality']}")

# Initialize OpenAI client with explicit configuration
api_key = os.getenv('OPENAI_API_KEY')
print(f"Debug: API key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"Debug: API key starts with: {api_key[:10]}...")

try:
    client = OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"Warning: OpenAI client initialization failed: {e}")
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception details: {str(e)}")
    client = None

# UNIVERSAL LLM FUNCTION (Document Agnostic)
def classify_with_llm(
    image_data: bytes,
    text_content: str,
    metadata: dict,
    industry: str = 'finance'
) -> dict:
    """
    Universal LLM classification function - completely document agnostic
    
    Args:
        image_data: Visual representation of document
        text_content: Extracted text content
        metadata: Document metadata (any structure)
        industry: Industry for category selection
    
    Returns:
        Classification result
    """
    
    # Get industry categories
    categories = get_categories_for_industry(industry)
    
    # Build universal prompt
    prompt = f"""
You are a document classification expert. Analyze this document and classify it.

DOCUMENT METADATA:
- Filename: {metadata.get('filename', 'unknown')}
- File Type: {metadata.get('file_type', 'unknown')}
- File Size: {metadata.get('file_size', 0)} bytes
- Pages/Sheets: {metadata.get('page_count', 1)}
"""

    # Add type-specific metadata dynamically
    for key, value in metadata.items():
        if key not in ['filename', 'file_type', 'file_size', 'page_count']:
            prompt += f"- {key.replace('_', ' ').title()}: {value}\n"

    # Add text content
    if text_content and text_content.strip():
        prompt += f"""
EXTRACTED TEXT (first 1000 characters):
{text_content[:1000]}
"""
    else:
        prompt += "\nEXTRACTED TEXT: None (image-only analysis)\n"

    # Add categories and instructions
    prompt += f"""
CLASSIFICATION CATEGORIES:
{', '.join(categories)}

INSTRUCTIONS:
1. Analyze both the visual content and extracted text
2. Consider all metadata provided
3. Choose the most appropriate category
4. Provide confidence level (0.0 to 1.0)

RESPONSE FORMAT (JSON only):
{{
    "classification": "category_name",
    "confidence": 0.95,
}}
"""
    
    # Call LLM
    llm_response = call_vision_llm(prompt, image_data)
    
    # Parse response
    return parse_llm_response(llm_response, categories)

def call_vision_llm(prompt: str, image_data: bytes) -> Dict[str, Any]:
    """
    Call LLM with image and text prompt
    
    Args:
        prompt: Text prompt for classification
        image_data: Image data as bytes
        
    Returns:
        LLM response dictionary
    """
    if client is None:
        return {
            'success': False,
            'error': 'OpenAI client not initialized',
            'content': None
        }
    
    try:
        # Convert image to base64 for API
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare messages based on model capabilities
        if MODEL in MODEL_INFO and MODEL_INFO[MODEL]["vision"]:
            # Vision-capable model - include image
            messages = [
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
            ]
        else:
            # Text-only model - use text content only
            messages = [
                {
                    "role": "user",
                    "content": prompt + "\n\nNote: Image analysis not available with this model. Classification based on text content only."
                }
            ]
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent classification
        )
        
        return {
            'success': True,
            'content': response.choices[0].message.content,
            'model': response.model,
            'usage': response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'content': None
        }

def parse_llm_response(llm_response: Dict[str, Any], valid_categories: list) -> Dict[str, Any]:
    """
    Parse and validate LLM response
    
    Args:
        llm_response: Response from LLM
        valid_categories: List of valid classification categories
        
    Returns:
        Parsed classification result
    """
    if not llm_response['success']:
        return {
            'classification': 'processing_error',
            'confidence': 0.0,
            'reasoning': f"LLM call failed: {llm_response['error']}"
        }
    
    try:
        content = llm_response['content']
        
        # Handle cases where LLM wraps JSON in markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        
        # Parse JSON response
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
        
    except json.JSONDecodeError as e:
        return {
            'classification': 'parsing_error',
            'confidence': 0.0,
            'reasoning': f"Failed to parse JSON response: {str(e)}"
        }
    except Exception as e:
        return {
            'classification': 'parsing_error',
            'confidence': 0.0,
            'reasoning': f"Failed to parse LLM response: {str(e)}"
        }
