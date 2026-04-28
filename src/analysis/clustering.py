"""
DBSCAN clustering on item embeddings to discover semantic themes.
"""
import numpy as np
from collections import Counter
from sklearn.cluster import DBSCAN
from src.db import get_all_items_with_embeddings, update_event_cluster, get_connection
from src.processing.embeddings import from_bytes
from src.config import DBSCAN_EPS as EPS, DBSCAN_MIN_SAMPLES as MIN_SAMPLES


def _top_keywords(texts: list[str], n: int = 3) -> str:
    import re
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "that", "this", "these",
        "those", "its", "their", "they", "it", "he", "she", "we", "you",
        "by", "from", "as", "not", "but", "more", "also", "new", "brand",
        "luxury", "fashion",
    }
    words: list[str] = []
    for text in texts:
        words.extend(re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))
    freq = Counter(w for w in words if w not in STOPWORDS)
    return " / ".join(w for w, _ in freq.most_common(n))


def run_clustering() -> dict[str, int]:
    """
    Returns a mapping of item_id → cluster_id.
    Cluster -1 means noise (no cluster assigned).
    """
    rows = get_all_items_with_embeddings()
    if len(rows) < MIN_SAMPLES:
        print("[Clustering] Not enough items to cluster.")
        return {}

    item_ids = [r["item_id"] for r in rows]
    embeddings = np.array([from_bytes(r["embedding"]) for r in rows], dtype=np.float32)

    # Convert cosine similarity → distance (DBSCAN uses distance)
    # Because embeddings are normalized, cosine_distance = 1 - dot_product
    db = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric="cosine")
    labels = db.fit_predict(embeddings)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"[Clustering] {n_clusters} clusters, {n_noise} noise points from {len(item_ids)} items")

    mapping = {item_id: int(label) for item_id, label in zip(item_ids, labels)}

    # Persist cluster assignments to events table
    with get_connection() as conn:
        for item_id, cluster_id in mapping.items():
            conn.execute(
                "UPDATE events SET cluster_id = ? WHERE item_id = ?",
                (cluster_id, item_id),
            )
        conn.commit()

    return mapping


def get_cluster_themes() -> dict[int, str]:
    """
    Returns a mapping of cluster_id → human-readable theme label.
    """
    rows = get_all_items_with_embeddings()
    if not rows:
        return {}

    conn = get_connection()
    cluster_texts: dict[int, list[str]] = {}
    for row in rows:
        res = conn.execute(
            "SELECT cluster_id FROM events WHERE item_id = ?", (row["item_id"],)
        ).fetchone()
        if res and res["cluster_id"] is not None and res["cluster_id"] != -1:
            cid = res["cluster_id"]
            title_row = conn.execute(
                "SELECT title, excerpt FROM items WHERE item_id = ?", (row["item_id"],)
            ).fetchone()
            if title_row:
                text = f"{title_row['title']} {title_row['excerpt'] or ''}"
                cluster_texts.setdefault(cid, []).append(text)
    conn.close()

    return {cid: _top_keywords(texts) for cid, texts in cluster_texts.items()}
