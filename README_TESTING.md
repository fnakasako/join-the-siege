# Testing the Document Classification API

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

### 3. Start the API
```bash
python run_api.py
```

### 4. Run Tests
```bash
# Automated testing with all files
python test_api.py

# Or test manually with curl
curl -X POST -F 'file=@files/invoice_1.pdf' http://127.0.0.1:5000/classify_file
```

## Available Test Files

Your `files/` directory contains:
- **PDFs**: `bank_statement_1.pdf`, `bank_statement_2.pdf`, `bank_statement_3.pdf`
- **PDFs**: `invoice_1.pdf`, `invoice_2.pdf`, `invoice_3.pdf`  
- **Images**: `drivers_license_1.jpg`, `drivers_licence_2.jpg`, `drivers_license_3.jpg`

## API Endpoints

### 1. Classify Document
```bash
POST /classify_file
```

**Parameters:**
- `file`: Document file (PDF, JPG, PNG, etc.)
- `industry`: Industry context (optional, default: 'finance')

**Example:**
```bash
curl -X POST \
  -F 'file=@files/invoice_1.pdf' \
  -F 'industry=finance' \
  http://127.0.0.1:5000/classify_file
```

**Response:**
```json
{
  "file_class": "invoice",
  "confidence": 0.95,
  "industry": "finance",
  "reasoning": "Document contains invoice header, line items, and total amount",
  "metadata": {
    "filename": "invoice_1.pdf",
    "file_type": "pdf",
    "file_size": 245760,
    "page_count": 1,
    "has_text": true
  }
}
```

### 2. Get Available Industries
```bash
GET /industries
```

**Response:**
```json
{
  "industries": ["finance", "legal", "healthcare", "real_estate", "insurance", "hr"]
}
```

### 3. Get Categories for Industry
```bash
GET /categories/{industry}
```

**Example:**
```bash
curl http://127.0.0.1:5000/categories/finance
```

**Response:**
```json
{
  "industry": "finance",
  "categories": [
    "invoice",
    "bank_statement",
    "financial_report",
    "contract",
    "receipt",
    "tax_document",
    "insurance_document",
    "loan_document",
    "unknown"
  ]
}
```

## Testing Different Industries

Test the same document with different industry contexts:

```bash
# Finance context
curl -X POST -F 'file=@files/invoice_1.pdf' -F 'industry=finance' http://127.0.0.1:5000/classify_file

# Legal context  
curl -X POST -F 'file=@files/invoice_1.pdf' -F 'industry=legal' http://127.0.0.1:5000/classify_file

# Healthcare context
curl -X POST -F 'file=@files/invoice_1.pdf' -F 'industry=healthcare' http://127.0.0.1:5000/classify_file
```

## Expected Results

Based on your test files, you should expect:

| File | Expected Classification | Confidence |
|------|------------------------|------------|
| `bank_statement_*.pdf` | `bank_statement` | High (>0.8) |
| `invoice_*.pdf` | `invoice` | High (>0.8) |
| `drivers_license_*.jpg` | `unknown` | Variable* |

*Note: Driver's licenses aren't in the finance categories, so they'll be classified as "unknown" unless you test with a different industry that includes ID documents.

## Troubleshooting

### Common Issues:

1. **"Cannot connect to API"**
   - Make sure Flask app is running: `python run_api.py`
   - Check if port 5000 is available

2. **"LLM call failed"**
   - Verify OpenAI API key is set: `echo $OPENAI_API_KEY`
   - Check your OpenAI account has credits
   - Ensure internet connection

3. **"File type not allowed"**
   - Check file extension is supported
   - Supported: PDF, JPG, PNG, GIF, BMP, TIFF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV

4. **"Processing error"**
   - Check file isn't corrupted
   - Ensure dependencies are installed: `pip install -r requirements.txt`

### Debug Mode:

Run the API in debug mode for more detailed error messages:
```bash
FLASK_DEBUG=1 python run_api.py
```

## Performance Notes

- **First request**: May take 10-15 seconds (cold start)
- **Subsequent requests**: 3-8 seconds per document
- **Cost**: ~$0.01-0.02 per document (OpenAI GPT-4V pricing)

## Next Steps

After testing, you can:
1. Add more test files to `files/` directory
2. Modify categories in `src/classifier/categories/industry_categories.json`
3. Test with different industries
4. Implement production features (rate limiting, caching, etc.)

## Fixed Import Issues

I've created `run_api.py` to avoid Python module import issues. Use this instead of `python -m src.app`.
