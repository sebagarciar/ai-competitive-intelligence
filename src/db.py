import json
import sqlite3
import uuid
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "intelligence.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                item_id          TEXT PRIMARY KEY,
                competitor       TEXT NOT NULL,
                source_type      TEXT NOT NULL,
                source_name      TEXT NOT NULL,
                source_url       TEXT UNIQUE NOT NULL,
                published_at     TEXT,
                title            TEXT,
                excerpt          TEXT,
                raw_text         TEXT,
                translated_text  TEXT,
                original_language TEXT,
                official_source  INTEGER DEFAULT 0,
                embedding        BLOB,
                sentiment_label  TEXT,
                sentiment_score  REAL,
                sentiment_confidence REAL,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id          TEXT PRIMARY KEY,
                item_id           TEXT NOT NULL REFERENCES items(item_id),
                competitor        TEXT NOT NULL,
                event_type        TEXT,
                business_function TEXT,
                relevance_score   REAL,
                impact_score      REAL,
                summary           TEXT,
                evidence_snippet  TEXT,
                confidence_score  REAL,
                duplicate_group_id TEXT,
                cluster_id        INTEGER DEFAULT -1,
                created_at        TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS trends (
                trend_id        TEXT PRIMARY KEY,
                competitor      TEXT NOT NULL,
                event_type      TEXT,
                cluster_id      INTEGER,
                count_7d        INTEGER,
                mean_prev_28d   REAL,
                std_prev_28d    REAL,
                unique_sources  INTEGER,
                unique_sources_7d INTEGER,
                avg_impact      REAL,
                burst_z         REAL,
                trend_score     REAL,
                is_critical     INTEGER DEFAULT 0,
                detected_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS brief_synthesis_cache (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                brand           TEXT NOT NULL,
                brief_date      TEXT,
                model           TEXT NOT NULL,
                prompt_hash     TEXT NOT NULL,
                output          TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(brand, prompt_hash)
            );

            CREATE INDEX IF NOT EXISTS idx_synth_lookup ON brief_synthesis_cache(brand, prompt_hash);
            CREATE INDEX IF NOT EXISTS idx_items_competitor ON items(competitor);
            CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
            CREATE INDEX IF NOT EXISTS idx_events_competitor ON events(competitor);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_trends_score ON trends(trend_score DESC);
        """)
        # Migrate pre-sentiment / pre-embedding-version schema — safe on new DBs too
        existing = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
        for col, typedef in [
            ("sentiment_label", "TEXT"),
            ("sentiment_score", "REAL"),
            ("sentiment_confidence", "REAL"),
            ("embedding_model", "TEXT"),
            ("engagement_metrics", "TEXT"),
        ]:
            if col not in existing:
                conn.execute(f"ALTER TABLE items ADD COLUMN {col} {typedef}")
        existing_trends = {row[1] for row in conn.execute("PRAGMA table_info(trends)")}
        if "avg_sentiment" not in existing_trends:
            conn.execute("ALTER TABLE trends ADD COLUMN avg_sentiment REAL")
        if "anomaly_score" not in existing_trends:
            conn.execute("ALTER TABLE trends ADD COLUMN anomaly_score REAL")
        if "unique_sources_7d" not in existing_trends:
            conn.execute("ALTER TABLE trends ADD COLUMN unique_sources_7d INTEGER")
        # Create sentiment index only after column is guaranteed to exist
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_sentiment ON items(sentiment_score)"
        )


# --- Item helpers ---

def url_exists(url: str) -> bool:
    with db() as conn:
        row = conn.execute("SELECT 1 FROM items WHERE source_url = ?", (url,)).fetchone()
        return row is not None


def insert_item(item: dict) -> str:
    item_id = item.get("item_id") or str(uuid.uuid4())
    engagement = item.get("engagement_metrics")
    engagement_json = json.dumps(engagement) if engagement else None
    with db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO items
                (item_id, competitor, source_type, source_name, source_url,
                 published_at, title, excerpt, raw_text, translated_text,
                 original_language, official_source, engagement_metrics)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            item_id,
            item.get("competitor"),
            item.get("source_type"),
            item.get("source_name"),
            item.get("source_url"),
            item.get("published_at"),
            item.get("title"),
            item.get("excerpt"),
            item.get("raw_text"),
            item.get("translated_text"),
            item.get("original_language"),
            int(item.get("official_source", False)),
            engagement_json,
        ))
    return item_id


def update_item_embedding(item_id: str, embedding_bytes: bytes, model_name: str = "") -> None:
    with db() as conn:
        conn.execute(
            "UPDATE items SET embedding = ?, embedding_model = ? WHERE item_id = ?",
            (embedding_bytes, model_name, item_id),
        )


def get_items_with_stale_embeddings(current_model: str) -> list[dict]:
    """Return items whose embedding was computed with a different (or unknown) model."""
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, title, excerpt FROM items WHERE embedding IS NOT NULL AND (embedding_model IS NULL OR embedding_model != ?)",
            (current_model,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_item_translation(item_id: str, translated_text: str, original_language: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE items SET translated_text = ?, original_language = ? WHERE item_id = ?",
            (translated_text, original_language, item_id),
        )


def get_items_without_embeddings() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, title, excerpt FROM items WHERE embedding IS NULL"
        ).fetchall()
        return [dict(r) for r in rows]


def get_items_without_sentiment() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, raw_text, translated_text FROM items WHERE sentiment_label IS NULL"
        ).fetchall()
        return [dict(r) for r in rows]


def update_item_sentiment(item_id: str, label: str, score: float, confidence: float) -> None:
    with db() as conn:
        conn.execute(
            """UPDATE items SET sentiment_label = ?, sentiment_score = ?,
               sentiment_confidence = ? WHERE item_id = ?""",
            (label, score, confidence, item_id),
        )


def get_all_items_with_embeddings() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, competitor, source_url, embedding FROM items WHERE embedding IS NOT NULL"
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_items(days: int = 30) -> list[dict]:
    with db() as conn:
        rows = conn.execute("""
            SELECT i.*, e.event_type, e.event_id, e.relevance_score, e.impact_score,
                   e.summary, e.evidence_snippet, e.confidence_score, e.cluster_id
            FROM items i
            LEFT JOIN events e ON i.item_id = e.item_id
            WHERE i.published_at >= datetime('now', ?)
            ORDER BY i.published_at DESC
        """, (f"-{days} days",)).fetchall()
        return [dict(r) for r in rows]


# --- Event helpers ---

def insert_event(event: dict) -> str:
    event_id = event.get("event_id") or str(uuid.uuid4())
    with db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO events
                (event_id, item_id, competitor, event_type, business_function,
                 relevance_score, impact_score, summary, evidence_snippet,
                 confidence_score, duplicate_group_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            event_id,
            event["item_id"],
            event["competitor"],
            event.get("event_type"),
            event.get("business_function"),
            event.get("relevance_score"),
            event.get("impact_score"),
            event.get("summary"),
            event.get("evidence_snippet"),
            event.get("confidence_score"),
            event.get("duplicate_group_id"),
        ))
    return event_id


def update_event_cluster(event_id: str, cluster_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE events SET cluster_id = ? WHERE event_id = ?", (cluster_id, event_id))


def get_events_for_trends(days: int = 35) -> list[dict]:
    with db() as conn:
        rows = conn.execute("""
            SELECT e.*, i.published_at, i.official_source, i.source_name, i.sentiment_score
            FROM events e
            JOIN items i ON e.item_id = i.item_id
            WHERE i.published_at >= datetime('now', ?)
        """, (f"-{days} days",)).fetchall()
        return [dict(r) for r in rows]


# --- Trend helpers ---

def insert_trend(trend: dict) -> str:
    trend_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute("""
            INSERT INTO trends
                (trend_id, competitor, event_type, cluster_id, count_7d,
                 mean_prev_28d, std_prev_28d, unique_sources, unique_sources_7d,
                 avg_impact, burst_z, trend_score, is_critical, avg_sentiment, anomaly_score)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            trend_id,
            trend["competitor"],
            trend["event_type"],
            trend.get("cluster_id", -1),
            trend["count_7d"],
            trend["mean_prev_28d"],
            trend["std_prev_28d"],
            trend["unique_sources"],
            trend.get("unique_sources_7d"),
            trend["avg_impact"],
            trend["burst_z"],
            trend["trend_score"],
            int(trend.get("is_critical", False)),
            trend.get("avg_sentiment"),
            trend.get("anomaly_score"),
        ))
    return trend_id


def get_latest_trends(limit: int = 20) -> list[dict]:
    with db() as conn:
        rows = conn.execute("""
            SELECT * FROM trends
            ORDER BY trend_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def clear_trends() -> None:
    with db() as conn:
        conn.execute("DELETE FROM trends")


# --- Brief synthesis cache helpers ---

def get_cached_synthesis(brand: str, prompt_hash: str) -> str | None:
    with db() as conn:
        row = conn.execute(
            "SELECT output FROM brief_synthesis_cache WHERE brand = ? AND prompt_hash = ?",
            (brand, prompt_hash),
        ).fetchone()
        return row["output"] if row else None


def cache_synthesis(brand: str, brief_date: str, model: str, prompt_hash: str, output: str) -> None:
    with db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO brief_synthesis_cache
               (brand, brief_date, model, prompt_hash, output)
               VALUES (?, ?, ?, ?, ?)""",
            (brand, brief_date, model, prompt_hash, output),
        )


def backfill_engagement_from_excerpt() -> int:
    """One-time migration: parse engagement_metrics from the legacy excerpt prefix.

    Supports the prefixes used by X, YouTube, Reddit, and Bluesky adapters.
    Returns the number of rows updated.
    """
    import re

    patterns = [
        (re.compile(r"^\[Likes:\s*(\d+),\s*Retweets:\s*(\d+)(?:,\s*Replies:\s*(\d+))?\]"),
         lambda m: {"likes": int(m.group(1)), "retweets": int(m.group(2)),
                    **({"replies": int(m.group(3))} if m.group(3) else {})}),
        (re.compile(r"^\[Views:\s*([\d,]+),\s*Likes:\s*([\d,]+)\]"),
         lambda m: {"views": int(m.group(1).replace(",", "")),
                    "likes": int(m.group(2).replace(",", ""))}),
        (re.compile(r"^\[Upvotes:\s*(\d+)(?:,\s*Comments:\s*(\d+))?\]"),
         lambda m: {"upvotes": int(m.group(1)),
                    **({"comments": int(m.group(2))} if m.group(2) else {})}),
        (re.compile(r"^\[Likes:\s*(\d+),\s*Reposts:\s*(\d+)(?:,\s*Replies:\s*(\d+))?\]"),
         lambda m: {"likes": int(m.group(1)), "reposts": int(m.group(2)),
                    **({"replies": int(m.group(3))} if m.group(3) else {})}),
    ]

    updated = 0
    with db() as conn:
        rows = conn.execute(
            "SELECT item_id, excerpt FROM items WHERE engagement_metrics IS NULL AND excerpt LIKE '[%'"
        ).fetchall()
        for row in rows:
            excerpt = row["excerpt"] or ""
            for pat, builder in patterns:
                m = pat.match(excerpt)
                if m:
                    metrics = builder(m)
                    conn.execute(
                        "UPDATE items SET engagement_metrics = ? WHERE item_id = ?",
                        (json.dumps(metrics), row["item_id"]),
                    )
                    updated += 1
                    break
    return updated


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
    n = backfill_engagement_from_excerpt()
    print(f"Back-filled engagement_metrics for {n} existing items")
