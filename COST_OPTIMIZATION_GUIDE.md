# OpenAI Model Cost Optimization Guide

## Current Model Options & Costs

### 1. GPT-4o (Default)
- **Cost**: $0.005 input / $0.015 output per 1K tokens
- **Vision Support**: ✅ Yes
- **Quality**: Highest
- **Best For**: Production use where accuracy is critical

### 2. GPT-4o-mini (Recommended for Cost Savings)
- **Cost**: $0.00015 input / $0.0006 output per 1K tokens
- **Vision Support**: ✅ Yes  
- **Quality**: High (very close to GPT-4o)
- **Cost Savings**: ~97% cheaper than GPT-4o
- **Best For**: Most document classification tasks

### 3. GPT-3.5-turbo (Text-Only Budget Option)
- **Cost**: $0.0005 input / $0.0015 output per 1K tokens
- **Vision Support**: ❌ No (text extraction only)
- **Quality**: Medium
- **Cost Savings**: ~90% cheaper than GPT-4o
- **Best For**: Text-heavy documents where visual layout isn't critical

## Cost Comparison Example

For 1,000 document classifications (assuming ~1K tokens input, 100 tokens output):

| Model | Input Cost | Output Cost | Total Cost | Savings vs GPT-4o |
|-------|------------|-------------|------------|-------------------|
| GPT-4o | $5.00 | $1.50 | **$6.50** | - |
| GPT-4o-mini | $0.15 | $0.06 | **$0.21** | 97% ($6.29) |
| GPT-3.5-turbo | $0.50 | $0.15 | **$0.65** | 90% ($5.85) |

## How to Test Different Models

### Method 1: Environment Variable (Recommended)
Edit your `.env` file and uncomment one of these lines:

```bash
# For maximum cost savings with vision support
OPENAI_MODEL=gpt-4o-mini

# For text-only budget option
OPENAI_MODEL=gpt-3.5-turbo

# For highest quality (default)
OPENAI_MODEL=gpt-4o
```

### Method 2: Docker Environment Override
```bash
# Test with GPT-4o-mini
docker-compose down
OPENAI_MODEL=gpt-4o-mini docker-compose up

# Test with GPT-3.5-turbo
docker-compose down
OPENAI_MODEL=gpt-3.5-turbo docker-compose up
```

## Testing Strategy

1. **Start with GPT-4o-mini**: Test with your typical documents
2. **Compare accuracy**: Run the same documents through different models
3. **Measure performance**: Check confidence scores and classification accuracy
4. **Calculate ROI**: Determine if the cost savings justify any accuracy trade-offs

## Performance Expectations

### GPT-4o-mini vs GPT-4o
- **Accuracy**: 95-98% similar performance
- **Vision capabilities**: Nearly identical
- **Speed**: Slightly faster
- **Cost**: 97% cheaper

### GPT-3.5-turbo Limitations
- **No vision**: Relies only on extracted text
- **Lower accuracy**: For visually complex documents
- **Good for**: Text-heavy documents (invoices, contracts, reports)
- **Not ideal for**: Image-heavy documents, complex layouts

## Monitoring Costs

The system logs model information on startup:
```
Using model: gpt-4o-mini
Model info - Input: $0.00015/1K tokens, Output: $0.0006/1K tokens, Vision: True, Quality: high
```

## Recommendations

1. **Start with GPT-4o-mini** for most use cases
2. **Use GPT-3.5-turbo** for high-volume, text-heavy processing
3. **Reserve GPT-4o** for critical accuracy requirements
4. **A/B test** with your specific document types
5. **Monitor** classification confidence scores to ensure quality

## Quick Test Commands

```bash
# Test current model
curl -X POST -F 'file=@files/invoice_1.pdf' http://localhost:5000/classify_file

# Check which model is being used
docker-compose logs document-classifier | grep "Using model"
