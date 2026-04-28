"""
Two-stage deduplication:
  1. URL exact-match (checked before DB insert)
  2. Semantic cosine similarity on embeddings (threshold 0.92)
"""
import uuid
import numpy as np
from src.db import get_all_items_with_embeddings
from src.processing.embeddings import from_bytes
from src.config import SEMANTIC_SIMILARITY_THRESHOLD as SEMANTIC_THRESHOLD


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Embeddings are already L2-normalized, so dot product = cosine similarity
    return float(np.dot(a, b))


def assign_duplicate_groups(new_items: list[dict]) -> list[dict]:
    """
    Given a list of items that already have embeddings (as numpy arrays under key 'embedding_vec'),
    compare against existing DB embeddings and each other.
    Assigns a 'duplicate_group_id' to each item.
    """
    existing = get_all_items_with_embeddings()

    # Build existing (item_id, url, embedding) reference list
    existing_refs: list[tuple[str, str, np.ndarray]] = []
    for row in existing:
        if row["embedding"]:
            vec = from_bytes(row["embedding"])
            existing_refs.append((row["item_id"], row["source_url"], vec))

    # Group-id map: item_id → group_id
    group_map: dict[str, str] = {}

    def get_or_create_group(item_id: str) -> str:
        if item_id not in group_map:
            group_map[item_id] = str(uuid.uuid4())
        return group_map[item_id]

    for item in new_items:
        vec = item.get("embedding_vec")
        if vec is None:
            item["duplicate_group_id"] = str(uuid.uuid4())
            continue

        matched_group: str | None = None

        # Compare against existing DB items
        for ref_id, _, ref_vec in existing_refs:
            if cosine_similarity(vec, ref_vec) >= SEMANTIC_THRESHOLD:
                matched_group = get_or_create_group(ref_id)
                break

        # Compare against other new items already processed
        if matched_group is None:
            for other in new_items:
                if other is item:
                    continue
                other_vec = other.get("embedding_vec")
                if other_vec is None:
                    continue
                if cosine_similarity(vec, other_vec) >= SEMANTIC_THRESHOLD:
                    other_id = other.get("item_id", "")
                    if other_id:
                        matched_group = get_or_create_group(other_id)
                    break

        item["duplicate_group_id"] = matched_group or str(uuid.uuid4())

    return new_items
