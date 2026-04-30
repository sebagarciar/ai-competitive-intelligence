"""
Trend detection using the burst formula from the project spec.
IsolationForest anomaly scores are computed across all candidate groups
and stored alongside the hand-tuned trend_score.
"""
import math
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from src.db import get_events_for_trends, insert_trend, clear_trends
from src.config import (
    TREND_SCORE_THRESHOLD,
    MIN_UNIQUE_SOURCES,
    CRITICAL_IMPACT_THRESHOLD,
    TREND_WEIGHT_BURST,
    TREND_WEIGHT_SOURCES,
    TREND_WEIGHT_IMPACT,
    TREND_WEIGHT_SENTIMENT,
)


def _parse_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def detect_trends() -> list[dict]:
    now = datetime.now(timezone.utc)
    window_7d = now - timedelta(days=7)
    window_28d = now - timedelta(days=28)

    events = get_events_for_trends(days=35)
    if not events:
        print("[Trends] No events found.")
        return []

    # Group by (competitor, event_type, cluster_id)
    GroupKey = tuple[str, str, int]
    group_events: dict[GroupKey, list[dict]] = defaultdict(list)

    for ev in events:
        key: GroupKey = (
            ev["competitor"],
            ev["event_type"] or "unknown",
            ev["cluster_id"] if ev["cluster_id"] is not None else -1,
        )
        group_events[key].append(ev)

    clear_trends()
    trends: list[dict] = []

    for (competitor, event_type, cluster_id), group in group_events.items():
        published_dates = [_parse_dt(ev["published_at"]) for ev in group]
        published_dates = [d for d in published_dates if d]

        count_7d = sum(1 for d in published_dates if d >= window_7d)
        prev_28d_events = [ev for ev, d in zip(group, published_dates) if window_28d <= d < window_7d]

        if not prev_28d_events:
            mean_prev_28d = 0.0
            std_prev_28d = 0.0
        else:
            # Weekly counts within prev 28d window (4 weeks)
            weekly: list[int] = []
            for week_offset in range(4):
                week_start = window_28d + timedelta(weeks=week_offset)
                week_end = week_start + timedelta(weeks=1)
                c = sum(
                    1 for ev, d in zip(group, published_dates)
                    if d and week_start <= d < week_end
                )
                weekly.append(c)
            mean_prev_28d = sum(weekly) / 4
            variance = sum((w - mean_prev_28d) ** 2 for w in weekly) / 4
            std_prev_28d = math.sqrt(variance)

        unique_sources = len({ev["source_name"] for ev in group})
        impact_scores = [ev["impact_score"] for ev in group if ev.get("impact_score")]
        avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0.0
        sentiment_scores = [ev["sentiment_score"] for ev in group if ev.get("sentiment_score") is not None]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

        burst_z = (count_7d - mean_prev_28d) / (std_prev_28d + 1)
        trend_score = (
            TREND_WEIGHT_BURST * burst_z
            + TREND_WEIGHT_SOURCES * math.log(1 + unique_sources)
            + TREND_WEIGHT_IMPACT * (avg_impact / 5)
            + TREND_WEIGHT_SENTIMENT * avg_sentiment
        )

        has_official = any(ev.get("official_source") for ev in group)
        max_impact = max((ev.get("impact_score") or 0) for ev in group)

        qualifies = trend_score >= TREND_SCORE_THRESHOLD and (
            unique_sources >= MIN_UNIQUE_SOURCES
            or (has_official and max_impact >= CRITICAL_IMPACT_THRESHOLD)
        )

        if not qualifies:
            continue

        is_critical = (
            count_7d == 1
            and max_impact >= CRITICAL_IMPACT_THRESHOLD
            and (has_official or unique_sources >= 1)
        )

        trends.append({
            "competitor": competitor,
            "event_type": event_type,
            "cluster_id": cluster_id,
            "count_7d": count_7d,
            "mean_prev_28d": round(mean_prev_28d, 3),
            "std_prev_28d": round(std_prev_28d, 3),
            "unique_sources": unique_sources,
            "avg_impact": round(avg_impact, 2),
            "avg_sentiment": round(avg_sentiment, 3),
            "burst_z": round(burst_z, 3),
            "trend_score": round(trend_score, 3),
            "is_critical": is_critical,
            # feature vector for anomaly detection (stored separately before normalisation)
            "_features": [burst_z, math.log(1 + unique_sources), avg_impact / 5, avg_sentiment],
        })

    # ── IsolationForest anomaly scoring ──────────────────────
    # Fit on the 4-dim feature space (burst_z, log_sources, impact/5, sentiment)
    # across all qualifying trend groups. anomaly_score is in [-1, 0]: more negative = more anomalous.
    if len(trends) >= 4:
        try:
            from sklearn.ensemble import IsolationForest
            X = np.array([t["_features"] for t in trends], dtype=float)
            iso = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            raw_scores = iso.score_samples(X)  # lower = more anomalous
            # Normalise to [0, 1] where 1 = most anomalous
            lo, hi = raw_scores.min(), raw_scores.max()
            span = hi - lo if hi > lo else 1.0
            for trend, raw in zip(trends, raw_scores):
                trend["anomaly_score"] = round(float((hi - raw) / span), 4)
        except ImportError:
            print("[Trends] sklearn not available; anomaly_score skipped")
    else:
        for trend in trends:
            trend["anomaly_score"] = None

    for trend in trends:
        trend.pop("_features", None)
        insert_trend(trend)

    print(f"[Trends] {len(trends)} trends detected")
    return trends
