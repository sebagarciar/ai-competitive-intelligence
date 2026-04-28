"""
End-to-end pipeline orchestrator.

Usage:
    python -m src.pipeline          # run full pipeline
    python -m src.pipeline --ingest # ingestion only
"""
import argparse
import uuid
import numpy as np
from src.db import (
    init_db, url_exists, insert_item, update_item_embedding,
    update_item_translation, get_items_without_embeddings,
    get_items_without_sentiment, update_item_sentiment,
)
from src.ingestion import gdelt, rss_feeds, brand_sites, youtube, webhose, reddit, twitter
from src.processing.normalizer import normalize_item
from src.processing.language import process_language
from src.processing.embeddings import embed_batch, to_bytes, item_text
from src.processing.dedup import assign_duplicate_groups
from src.processing.extractor import extract_event
from src.processing.sentiment import analyze_batch
from src.analysis.clustering import run_clustering
from src.analysis.trends import detect_trends
from src.output.brief import generate_brief
from src.db import insert_event


def ingest() -> int:
    """Pull raw articles from all sources and store in DB."""
    all_raw = []
    all_raw.extend(gdelt.fetch_all())
    all_raw.extend(rss_feeds.fetch_all())
    all_raw.extend(brand_sites.fetch_all())
    all_raw.extend(youtube.fetch_all())
    all_raw.extend(webhose.fetch_all())
    # Social listening sources
    all_raw.extend(reddit.fetch_all())
    all_raw.extend(twitter.fetch_all())

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

    print(f"[Pipeline] Ingested {new_count} new items")
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
        update_item_embedding(item["item_id"], to_bytes(emb))

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


def extract() -> None:
    """Extract events from all embedded items that don't yet have an event record."""
    from src.db import get_connection
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.item_id, i.competitor, i.source_name, i.source_url,
               i.title, i.excerpt, i.raw_text, i.translated_text,
               i.original_language, i.official_source
        FROM items i
        LEFT JOIN events e ON i.item_id = e.item_id
        WHERE e.event_id IS NULL
    """).fetchall()
    conn.close()

    items = [dict(r) for r in rows]
    if not items:
        print("[Pipeline] No new items to extract events from.")
        return

    for item in items:
        event = extract_event(item, use_zero_shot=False)
        insert_event(event)

    print(f"[Pipeline] Extracted events for {len(items)} items")


def run_pipeline(skip_ingest: bool = False) -> None:
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
    extract()
    run_clustering()
    detect_trends()
    brief = generate_brief()

    print("\n" + "=" * 60)
    print("Pipeline complete. Brief preview (first 500 chars):")
    print("=" * 60)
    print(brief[:500])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the intelligence pipeline")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion step")
    args = parser.parse_args()
    run_pipeline(skip_ingest=args.skip_ingest)
