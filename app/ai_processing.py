from textblob import TextBlob
from transformers import pipeline
from typing import List, Dict
import numpy as np
import asyncio




# Function to Analyze Sentiment
def analyze_sentiment(comments: List[str]) -> Dict[str, float]:
    """
    Analyze sentiment of a list of comments.

    :param comments: List of comment texts.
    :return: A dictionary with average sentiment score and polarity breakdown.
    """
    sentiments = []

    for comment in comments:
        blob = TextBlob(comment)
        sentiments.append(blob.sentiment.polarity)  # Polarity score (-1 to 1)

    # Average Sentiment
    average_sentiment = np.mean(sentiments) if sentiments else 0
    return {
        "average_sentiment": average_sentiment,
        "sentiments": sentiments,
    }

# Initialize Sentiment Analysis Model
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Advanced Sentiment Analysis Function
def advanced_sentiment_analysis(comments: List[str]) -> Dict[str, float]:
    """
    Perform advanced sentiment analysis on a list of comments.

    :param comments: List of comment texts.
    :return: A dictionary with average sentiment score and polarity breakdown.
    """
    sentiments = []

    for comment in comments:
        # Use the pre-trained model for sentiment classification
        result = sentiment_pipeline(comment)
        label = result[0]['label']  # Positive or Negative
        score = result[0]['score']  # Confidence score

        # Convert label to polarity score: Positive -> 1, Negative -> -1
        polarity = score if label == 'POSITIVE' else -score
        sentiments.append(polarity)

    # Average Sentiment
    average_sentiment = np.mean(sentiments) if sentiments else 0

    return {
        "average_sentiment": average_sentiment,
        "sentiments": sentiments,
    }
