My priorities were:

1. Development velocity
2. Accuracy
3. Availability
4/5. Costs & Latency

I'll justify my prioritization below and walk through how the buffed classifier works. 

1. Development velocity

Given that Heron is an early stage company, revenue capture takes precedence--provide the services at the quality demanded by the industry (keep your customers as happy as possible). For this reason, I prioritzed development velocity. This lead me to adopting the *initial* method of using different LLM APIs to categorize the documents. This provides an extremely scalable approach which should generalize to any industry. The alternative here would have been to train a classification model, but this would not scale as you would have to retain a model, or retrain new models for specific industries. Additionally, if a new category of documents were added to a pre-existing industry, a classification based model like Bert would again fail to scale due to the necessity of retraining. As constructed, the classifier would work for any industry and any category of documents (given that the industry isn't extremely niche and out of scope of LLM's training data).

The approach that I took was to create a dictionary which is used to format LLM prompts:

{industry: [categories]}

When the classifier api is called, the industry is passed to the api. The categories are retrieved from the dictionary and passed to the LLM call. The LLM is forced to select from the given categories. This helps reduce the non-determinism of LLMs. Expanding the classifier to new industries or new categories only calls for the dictionary to be adjusted (add new industry with corresponding categories, adjust pre-existing categories, etc). 

2.

The other reason why I heavily relied on LLMs in my initial approach is due to accuracy constraints. Since we're working in finance, accuracy is absolutely paramount. While it is better if it is avoided altogether, it is better to have to wait 5 seconds before displaying someone's checkings account information rather than instantly providing inaccurate information. Classification models' accuracy within the scope of this exercise would plateau around 90%, and for finance, I would say that anything below 99.9999% accuracy is unacceptable. While LLMs wouldn't definitively get us there, they would be far more accurate than classification models within the scope of this assignment, both in its classification capabilities itself, and due to the fact that it can be prompted to provide a confidence rating on his assessment, which can be used to add fallbacks aimed at increasing accuracy. 

To expand on this, the classifier has a confidence threshold. The LLM is prompted to assert how confident they are in their classification from 0-100%. If their confidence is below a given threshold (currently set to 80%), the classfication task is passed to a more capable LLM. This allows us to keep down costs by selectively relying on more performant and expensive LLMs. We could also build on top of this architecture, using something like an assembly of LLMs to come to a ruling (though at that point it would be better to just return 'unkown' for the category).

3. 

Again, since Heron Data is an early stage company, I view revenue capture as the #1 priority. Margins can be improved afterwards. Given this, high availability takes precedence after accuracy. While this isn't something like trading where lack of availability for a few hours leads to millions of dollars lost, you will lose customers if they are inconvenienced. Given this, the way that I approached availability was by providing backup apis & rate limiting the current apis to avoid rate limits. Some rough estimates for this first draft of the classifier:

Tokens per request: 30k~ Can be significantly reduced

The current LLM hierarchy is:

gpt-4o-mini (cheap vision model) -> 0.000
gpt-4o
Claude sonnet-3.7
Google Gemini 2.0

# Need to include costs and token limits above to calculate costs and rate limits

4/5. Given that the above is taken care of, we have a high quality product that is highly available. The next step would be to make the margins as favoruable as possible by making the model usage cheap, and reducing latency. Right now the system has high latency (2-3 seconds for a response). There are a lot of ways to make these improvements:

1. Fine-tuning a smaller, cheaper model:
 - Distilling capabilities from a larger model into a smaller, much cheaper model
 - Training smaller models on similar documents 
 - etc
 - expand more
 - Use classification models for specific industries 
 - Only provide image if text only classification confidence drops below a certain level

 # Expand on more possibilities above


 - We would also want to create a testing/evaluation infrastructure to compare the latency & accuracy of the changes that we would make. # expand on eval infrastructure  




 The above gives us a very accurate and available classifier with a roadmap to make the classifier cheap and fast. (Also shouldn't be too difficult to make these improvements)




