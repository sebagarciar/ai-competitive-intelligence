"""
Sentiment analysis using local transformer models (no paid APIs).
Uses cardiffnlp/twitter-roberta-base-sentiment-latest for social media text.
Model optimized for tweets but works well for all short-form social content.
"""
from typing import Any
from transformers import pipeline
from functools import lru_cache

# Global singleton for lazy loading
_sentiment_pipeline = None


@lru_cache(maxsize=1)
def _load_sentiment_model() -> Any:
    """Load sentiment model once and cache it (lazy singleton pattern)."""
    print("[Sentiment] Loading cardiffnlp/twitter-roberta-base-sentiment-latest...")
    return pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        max_length=512,
        truncation=True,
    )


def get_sentiment_pipeline() -> Any:
    """Get or create the global sentiment pipeline."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        _sentiment_pipeline = _load_sentiment_model()
    return _sentiment_pipeline


def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using local transformer model.

    Returns:
        {
            "label": "positive" | "negative" | "neutral",
            "score": float (0-1 confidence),
            "sentiment_score": float (-1 to +1, normalized for sorting)
        }
    """
    if not text or len(text.strip()) < 10:
        return {
            "label": "neutral",
            "score": 0.0,
            "sentiment_score": 0.0,
        }

    try:
        pipeline = get_sentiment_pipeline()

        # Truncate very long text (model max is 512 tokens)
        text_truncated = text[:2000]

        result = pipeline(text_truncated)[0]

        # Normalize label to lowercase
        label = result["label"].lower()
        confidence = result["score"]

        # Create normalized sentiment score (-1 to +1) for easier sorting/filtering
        if label == "positive":
            sentiment_score = confidence
        elif label == "negative":
            sentiment_score = -confidence
        else:  # neutral
            sentiment_score = 0.0

        return {
            "label": label,
            "score": confidence,
            "sentiment_score": sentiment_score,
        }

    except Exception as e:
        print(f"[Sentiment] Error analyzing text: {e}")
        return {
            "label": "neutral",
            "score": 0.0,
            "sentiment_score": 0.0,
        }


def analyze_batch(texts: list[str], batch_size: int = 8) -> list[dict]:
    """
    Analyze sentiment for multiple texts in batches (more efficient).

    Args:
        texts: List of text strings to analyze
        batch_size: Number of texts to process at once

    Returns:
        List of sentiment dicts matching input order
    """
    if not texts:
        return []

    try:
        pipeline = get_sentiment_pipeline()

        # Filter empty texts, keep track of indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and len(text.strip()) >= 10:
                valid_texts.append(text[:2000])  # Truncate
                valid_indices.append(i)

        if not valid_texts:
            return [{"label": "neutral", "score": 0.0, "sentiment_score": 0.0}] * len(texts)

        # Run batch inference
        results = pipeline(valid_texts, batch_size=batch_size)

        # Map results back to original indices
        output = []
        result_idx = 0

        for i in range(len(texts)):
            if i in valid_indices:
                result = results[result_idx]
                label = result["label"].lower()
                confidence = result["score"]

                if label == "positive":
                    sentiment_score = confidence
                elif label == "negative":
                    sentiment_score = -confidence
                else:
                    sentiment_score = 0.0

                output.append({
                    "label": label,
                    "score": confidence,
                    "sentiment_score": sentiment_score,
                })
                result_idx += 1
            else:
                # Empty text, return neutral
                output.append({
                    "label": "neutral",
                    "score": 0.0,
                    "sentiment_score": 0.0,
                })

        return output

    except Exception as e:
        print(f"[Sentiment] Error in batch analysis: {e}")
        return [{"label": "neutral", "score": 0.0, "sentiment_score": 0.0}] * len(texts)


def get_sentiment_category(sentiment_score: float) -> str:
    """
    Convert numerical sentiment score to category for easy filtering.

    Args:
        sentiment_score: Normalized score from -1 (very negative) to +1 (very positive)

    Returns:
        "very_positive" | "positive" | "neutral" | "negative" | "very_negative"
    """
    if sentiment_score >= 0.6:
        return "very_positive"
    elif sentiment_score >= 0.2:
        return "positive"
    elif sentiment_score >= -0.2:
        return "neutral"
    elif sentiment_score >= -0.6:
        return "negative"
    else:
        return "very_negative"
