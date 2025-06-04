My priorities were:

1. Development velocity
2. Accuracy
3. Availability
4/5. Costs & Latency

I'll justify my prioritization below and walk through how the classifier works. 

# 1. Development velocity

Given that Heron is an early stage company, revenue capture takes precedence. For this reason, I prioritzed development velocity. This lead me to adopting the *initial* method of using different LLM APIs to categorize the documents. This is a scalable approach which generalizes to nearly any industry. The alternative here would have been to train a classification model, but this would not scale as you would have to retrain models for new industries. As constructed, the classifier would work for any industry and any category of documents (given that the industry isn't extremely niche and out of scope of LLMs' training data).

The approach that I took was to create a dictionary which is used to format LLM prompts:

{industry: [categories]}

When the classifier api is called, the industry is passed in the call. The categories are retrieved from the dictionary and passed to the LLM call. The LLM is forced to select from the given categories. This helps reduce the non-determinism of LLMs. Expanding the classifier to new industries or new categories only calls for the dictionary to be adjusted (add new industry with corresponding categories, adjust pre-existing categories, etc). 

# 2. Accuracy

The other reason why I heavily relied on LLMs in my initial approach is due to accuracy requirements. Since we're working in finance, accuracy is absolutely paramount. While it is better if avoided altogether, it is better to have to wait 5 seconds before displaying someone's checkings account information rather than instantly providing inaccurate information. In my opinion, this applies to nearly all of finance. 

Classification models' accuracy within the scope of this exercise would plateau around 90%, and for finance, I would say that that is unacceptable. While LLMs wouldn't definitively get us there, they would be far more accurate than classification models within the scope of this assignment. This is further solidified by the fact that we can prompt LLMs to provide a confidence rating to its classification, which we can use to build in guard rails.


# 3. Availability

Margins on technical costs can be improved afterwards, quickly. Given this, high availability takes precedence after accuracy. 

The way that I approached availability was by providing backup llm apis & rate limiting the current apis. Some rough estimates for this first draft of the classifier:

Tokens per request: 30k~ (can be significantly reduced)

The current LLM hierarchy is:

gpt-4o-mini (cheap vision model)
gpt-4o
Claude sonnet-3.7
Google Gemini 2.0

## Capacity & Cost Analysis

### Token Limits & Rate Limits by Provider (Production Tier):
- **GPT-4o-mini**: 2M TPM, $0.15/1M input tokens, $0.60/1M output tokens
- **GPT-4o**: 800K TPM, $2.50/1M input tokens, $10.00/1M output tokens  
- **Claude Sonnet 3.5**: 400K TPM, $3.00/1M input tokens, $15.00/1M output tokens
- **Gemini 2.0**: 1M TPM, $1.25/1M input tokens, $5.00/1M output tokens

### Capacity Calculations (30K tokens per document):
- **GPT-4o-mini**: 2M TPM ÷ 30K = ~67 documents/minute = ~96K documents/day
- **GPT-4o**: 800K TPM ÷ 30K = ~27 documents/minute = ~39K documents/day
- **Claude Sonnet**: 400K TPM ÷ 30K = ~13 documents/minute = ~19K documents/day
- **Gemini 2.0**: 1M TPM ÷ 30K = ~33 documents/minute = ~48K documents/day

### Cost Calculations (per 1000 documents):
Assuming 30K tokens per request (25K input + 5K output):
- **GPT-4o-mini**: $0.15 × 25 + $0.60 × 5 = $6.75 per 1000 documents
- **GPT-4o**: $2.50 × 25 + $10.00 × 5 = $112.50 per 1000 documents
- **Claude Sonnet**: $3.00 × 25 + $15.00 × 5 = $150.00 per 1000 documents
- **Gemini 2.0**: $1.25 × 25 + $5.00 × 5 = $56.25 per 1000 documents

### Overall System Capacity:
- **Combined theoretical capacity**: ~140 documents/minute = ~200K documents/day
- **Realistic capacity with failover**: ~100K documents/day (accounting for load balancing)
- **Scaling strategy**: Multiple API keys per provider can multiply these limits
- **Cost optimization**: 95% traffic on GPT-4o-mini keeps costs at ~$7/1000 documents

# 4/5. Cost & Latency

Given that the above is taken care of, we now have a high quality product that is highly available. The next step would be to make classifier more accurate, cheaper, and faster. I would suggest using A/B testing to roll out improvements and to also implement Grafana or Datadog for monitoring.

Here are some possibilities for making the classifier cheaper & faster:

**Input token reduction:**
- **Smart Text Extraction**: Extract only relevant sections (headers, key paragraphs) instead of full document text
- **Image Processing**: Use OCR preprocessing to reduce vision model usage by 60-80%
- **Conditional Vision**: Only send images when text-only classification confidence drops below threshold


**1. LoRA (Low-Rank Adaptation) Fine-tuning:**
- Fine-tune only 0.1% of model parameters on document classification task
- Reduces inference cost by 60-80% while maintaining 95%+ accuracy
- Can be applied to Llama 3.1-8B to create specialized document classifier at $0.50/1000 docs

**2. Instruction Tuning for Structured Output:**
- Fine-tune smaller models (Mistral-7B) to follow classification instructions precisely
- Eliminates need for complex prompts, reducing token usage by 70%
- Target: <5K tokens per request vs current 30K

**3. Task-Specific Distillation:**
- Use GPT-4o outputs to train specialized BERT-large model for document classification
- Achieves 500ms latency vs 2-3 seconds, 95% cost reduction
- Maintains 94-96% accuracy for standard document types

### High-Accuracy Traditional ML Approaches:


**1. Transformer-based Classification Models:**
- Fine-tuned RoBERTa/DeBERTa on document classification: 96-98% accuracy
- Built-in confidence estimation through softmax probabilities
- 50-100ms inference time, $0.10/1000 documents



### LLM vs Traditional ML:


- **LLMs (GPT-4o)**: 96-98% accuracy, high cost, 2-3s latency
- **Fine-tuned Traditional ML**: 94-97% accuracy, low cost, <500ms latency
- **Hybrid Approach**: 97-99% accuracy (ML for common cases, LLM for edge cases)

