"""
End-to-end pipeline orchestrator.

Usage:
    python -m src.pipeline          # run full pipeline
    python -m src.pipeline --ingest # ingestion only
"""
import argparse
import uuid
from typing import Callable
import numpy as np
from src.db import (
    init_db, url_exists, insert_item, update_item_embedding,
    update_item_translation, get_items_without_embeddings,
    get_items_without_sentiment, update_item_sentiment,
)
from src.ingestion import rss_feeds, brand_sites, youtube, webhose, reddit, twitter, bluesky, grok_search
from src.processing.normalizer import normalize_item
from src.processing.language import process_language
from src.processing.embeddings import embed_batch, to_bytes, item_text, MODEL_NAME as EMBEDDING_MODEL
from src.processing.dedup import assign_duplicate_groups
from src.processing.extractor import extract_event
from src.processing.sentiment import analyze_batch
from src.analysis.clustering import run_clustering
from src.analysis.trends import detect_trends
from src.output.brief import generate_brief
from src.db import insert_event


def _fetch_simple(fetch_fn: Callable[..., list[dict]], name: str, min_results: int = 3) -> tuple[str, list[dict]]:
    """
    Call a social adapter that accepts simple=bool.
    If the full query returns fewer than min_results, retries with simple=True.
    Returns (name, items).
    """
    items = fetch_fn(simple=False)
    if len(items) < min_results:
        print(f"[Pipeline] {name}: only {len(items)} results, retrying with simple queries")
        items = fetch_fn(simple=True)
    return name, items


def ingest() -> int:
    """Pull raw articles from all sources and store in DB."""
    source_counts: dict[str, int] = {}
    all_raw: list[dict] = []

    # News and media sources (no query planning needed)
    for name, fn in [
        ("RSS", rss_feeds.fetch_all),
        ("Brand Sites", brand_sites.fetch_all),
        ("YouTube", youtube.fetch_all),
        ("Webhose", webhose.fetch_all),
        ("Twitter/X (ntscraper)", twitter.fetch_all),
    ]:
        items = fn()
        source_counts[name] = len(items)
        all_raw.extend(items)

    # Social sources with query planning + retry
    for name, fn in [
        ("Reddit", reddit.fetch_all),
        ("Bluesky", bluesky.fetch_all),
        ("X via Grok", grok_search.fetch_all),
    ]:
        _, items = _fetch_simple(fn, name)
        source_counts[name] = len(items)
        all_raw.extend(items)

    new_count = 0
    for raw_item in all_raw:
        if not raw_item.get("source_url"):
            continue
        if url_exists(raw_item["source_url"]):
            continue
        raw_item["item_id"] = str(uuid.uuid4())
        normalized = normalize_item(raw_item)
        processed = process_language(normalized)
        insert_item(processed)
        new_count += 1

    # Per-source summary
    print("\n[Pipeline] Source summary:")
    col_w = max(len(n) for n in source_counts) + 2
    for name, count in source_counts.items():
        status = "(unavailable)" if count == 0 else ""
        print(f"  {name:<{col_w}} {count:>4} items  {status}")
    print(f"  {'─' * (col_w + 14)}")
    print(f"  {'Total new:':<{col_w}} {new_count:>4} items")
    return new_count


def embed() -> None:
    """Compute and store embeddings for items that don't have one yet."""
    pending = get_items_without_embeddings()
    if not pending:
        print("[Pipeline] All items already have embeddings.")
        return

    texts = [item_text(p) for p in pending]
    embeddings: np.ndarray = embed_batch(texts)

    for item, emb in zip(pending, embeddings):
        update_item_embedding(item["item_id"], to_bytes(emb), EMBEDDING_MODEL)

    print(f"[Pipeline] Embedded {len(pending)} items")


def analyze_sentiment() -> None:
    """Analyze sentiment for items that don't have sentiment scores yet."""
    pending = get_items_without_sentiment()
    if not pending:
        print("[Pipeline] All items already have sentiment scores.")
        return

    # Use translated_text if available (English), otherwise raw_text
    texts = [
        item.get("translated_text") or item.get("raw_text", "")
        for item in pending
    ]

    # Batch sentiment analysis (more efficient than one-by-one)
    sentiments = analyze_batch(texts, batch_size=16)

    for item, sentiment in zip(pending, sentiments):
        update_item_sentiment(
            item["item_id"],
            sentiment["label"],
            sentiment["sentiment_score"],
            sentiment["score"],
        )

    print(f"[Pipeline] Analyzed sentiment for {len(pending)} items")


def extract(use_zero_shot: bool = True) -> None:
    """Extract events from all embedded items that don't yet have an event record."""
    from src.db import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.item_id, i.competitor, i.source_name, i.source_url,
               i.title, i.excerpt, i.raw_text, i.translated_text,
               i.original_language, i.official_source, i.embedding,
               i.engagement_metrics
        FROM items i
        LEFT JOIN events e ON i.item_id = e.item_id
        WHERE e.event_id IS NULL
    """).fetchall()
    conn.close()

    items = [dict(r) for r in rows]
    if not items:
        print("[Pipeline] No new items to extract events from.")
        return

    # Pre-warm brand reference embeddings so the first item doesn't pay the load cost
    try:
        from src.processing.extractor import _get_brand_ref_embedding, BRAND_REFERENCES
        for brand in BRAND_REFERENCES:
            _get_brand_ref_embedding(brand)
    except Exception:
        pass

    if use_zero_shot:
        # Pre-warm the zero-shot model once before the loop to avoid per-item startup cost
        try:
            from src.processing.extractor import _get_zs_pipeline
            _get_zs_pipeline()
        except Exception as e:
            print(f"[Pipeline] Zero-shot model unavailable, falling back to keywords only: {e}")
            use_zero_shot = False

    for item in items:
        event = extract_event(item, use_zero_shot=use_zero_shot)
        insert_event(event)

    print(f"[Pipeline] Extracted events for {len(items)} items")


def run_pipeline(skip_ingest: bool = False, use_llm: bool = True, use_zero_shot: bool = True) -> None:
    print("=" * 60)
    print("AI Competitive Intelligence Copilot — Pipeline Run")
    print("=" * 60)

    init_db()

    if not skip_ingest:
        ingest()
    else:
        print("[Pipeline] Skipping ingestion.")

    embed()
    analyze_sentiment()  # New: analyze sentiment after embedding
    extract(use_zero_shot=use_zero_shot)
    run_clustering()
    detect_trends()
    brief = generate_brief(use_llm=use_llm)

    print("\n" + "=" * 60)
    print("Pipeline complete. Brief preview (first 500 chars):")
    print("=" * 60)
    print(brief[:500])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the intelligence pipeline")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion step")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM-based brief synthesis (use rule-based implications)")
    parser.add_argument("--no-zero-shot", action="store_true", help="Use keyword-only event classification (faster, lower quality)")
    args = parser.parse_args()
    run_pipeline(skip_ingest=args.skip_ingest, use_llm=not args.no_llm, use_zero_shot=not args.no_zero_shot)
