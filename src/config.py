"""
Central home for ML/analysis thresholds and tuning constants.

All values can be overridden via environment variables (e.g. export DBSCAN_EPS=0.3).
Import from here instead of hardcoding inline.
"""
import os


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


# --- Deduplication ---
SEMANTIC_SIMILARITY_THRESHOLD: float = _float("SEMANTIC_SIMILARITY_THRESHOLD", 0.92)

# --- Event extraction ---
KEYWORD_CONFIDENCE_THRESHOLD: float = _float("KEYWORD_CONFIDENCE_THRESHOLD", 0.35)

# --- DBSCAN clustering ---
DBSCAN_EPS: float = _float("DBSCAN_EPS", 0.25)          # cosine distance threshold
DBSCAN_MIN_SAMPLES: int = _int("DBSCAN_MIN_SAMPLES", 2)  # min articles per cluster

# --- Trend detection ---
TREND_SCORE_THRESHOLD: float = _float("TREND_SCORE_THRESHOLD", 0.3)
MIN_UNIQUE_SOURCES: int = _int("MIN_UNIQUE_SOURCES", 1)
CRITICAL_IMPACT_THRESHOLD: float = _float("CRITICAL_IMPACT_THRESHOLD", 2.3)

# Trend score formula weights: score = W_BURST*burst_z + W_SOURCES*log(1+sources) + W_IMPACT*(impact/5) + W_SENTIMENT*avg_sentiment
TREND_WEIGHT_BURST: float = _float("TREND_WEIGHT_BURST", 0.45)
TREND_WEIGHT_SOURCES: float = _float("TREND_WEIGHT_SOURCES", 0.27)
TREND_WEIGHT_IMPACT: float = _float("TREND_WEIGHT_IMPACT", 0.18)
TREND_WEIGHT_SENTIMENT: float = _float("TREND_WEIGHT_SENTIMENT", 0.10)


def _bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# --- Trained event classifier ---
# Set USE_TRAINED_CLASSIFIER=1 after running the fine-tuning notebook to use the
# LogisticRegression model from data/event_classifier.joblib instead of keyword scoring.
USE_TRAINED_CLASSIFIER: bool = _bool("USE_TRAINED_CLASSIFIER", False)

# --- LLM-based brief synthesis (Ollama, local) ---
# Set LLM_SYNTHESIS_ENABLED=0 (or pass --no-llm to the pipeline) to fall back
# to the deterministic rule-based implications.
LLM_SYNTHESIS_ENABLED: bool = _bool("LLM_SYNTHESIS_ENABLED", True)
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TEMPERATURE: float = _float("OLLAMA_TEMPERATURE", 0.3)
OLLAMA_TIMEOUT: int = _int("OLLAMA_TIMEOUT", 60)
OLLAMA_SEED: int = _int("OLLAMA_SEED", 42)
