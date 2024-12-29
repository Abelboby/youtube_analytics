from textblob import TextBlob
from typing import List, Dict
import numpy as np
import gc
from app.utils import check_memory_usage

def analyze_sentiment(comments: List[str]) -> Dict[str, float]:
    """
    Analyze sentiment of a list of comments using TextBlob (lightweight).
    
    :param comments: List of comment texts
    :return: Dictionary with average sentiment score and polarity breakdown
    """
    sentiments = []
    
    # Process in smaller batches to manage memory
    batch_size = 100
    for i in range(0, len(comments), batch_size):
        batch = comments[i:i + batch_size]
        
        for comment in batch:
            try:
                blob = TextBlob(comment)
                sentiments.append(blob.sentiment.polarity)
            except Exception:
                continue
                
        # Force garbage collection after each batch
        gc.collect()
    
    # Average Sentiment
    average_sentiment = np.mean(sentiments) if sentiments else 0
    
    return {
        "average_sentiment": average_sentiment,
        "sentiments": sentiments,
    }

# Remove the transformers pipeline and use only TextBlob
def advanced_sentiment_analysis(comments: List[str]) -> Dict[str, float]:
    """
    Perform sentiment analysis using TextBlob with memory optimization.
    
    :param comments: List of comment texts
    :return: Dictionary with sentiment analysis results
    """
    # Check memory usage
    mem_info = check_memory_usage()
    if mem_info['memory_percent'] > 80:  # Memory threshold
        # Fall back to processing fewer comments if memory is high
        comments = comments[:100]
    
    return analyze_sentiment(comments)
