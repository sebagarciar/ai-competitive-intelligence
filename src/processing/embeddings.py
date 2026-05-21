"""
Sentence embeddings using sentence-transformers (local, no API key needed).
Model: all-MiniLM-L6-v2 — fast, 384-dim, good for semantic similarity.
"""
import numpy as np

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Semantic search is unavailable in this deployment."
            )
        print(f"[Embeddings] Loading model {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def embed_batch(texts: list[str]) -> np.ndarray:
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 20)


def to_bytes(embedding: np.ndarray) -> bytes:
    return embedding.astype(np.float32).tobytes()


def from_bytes(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


def item_text(item: dict) -> str:
    title = item.get("title") or ""
    excerpt = item.get("translated_text") or item.get("excerpt") or ""
    return f"{title} {excerpt}".strip()
