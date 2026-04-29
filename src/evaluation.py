"""
Reusable metric functions for evaluating pipeline output quality.

Used by notebooks/evaluation.ipynb; can also be imported in tests.
All functions accept human-provided label lists and return scalar scores.
"""
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from sklearn.metrics import f1_score, classification_report

EVENT_TYPES = [
    "collection_launch",
    "campaign_or_collaboration",
    "pricing_or_exclusivity",
    "geographic_expansion",
    "creative_direction",
    "sustainability_or_sourcing",
    "celebrity_or_influencer_alignment",
    "reputational_issue",
]


def precision_at_k(labels: list[int], k: int = 10) -> float:
    """Fraction of the top-k items judged relevant (label == 1)."""
    subset = labels[:k]
    if not subset:
        return 0.0
    return sum(subset) / len(subset)


def event_f1(y_true: list[str], y_pred: list[str]) -> dict:
    """
    Compute macro and weighted F1 for event classification.

    Returns a dict with keys: macro, weighted, report (full text).
    """
    macro = f1_score(y_true, y_pred, labels=EVENT_TYPES, average="macro", zero_division=0)
    weighted = f1_score(y_true, y_pred, labels=EVENT_TYPES, average="weighted", zero_division=0)
    report = classification_report(y_true, y_pred, labels=EVENT_TYPES, zero_division=0)
    return {"macro": macro, "weighted": weighted, "report": report}


def trend_precision_at_k(labels: list[int], k: int = 5) -> float:
    """Fraction of the top-k trends judged valid (label == 1)."""
    return precision_at_k(labels, k)


# ---------------------------------------------------------------------------
# Trend formula weight ablation
# ---------------------------------------------------------------------------

def _compute_trend_rows(events: list[dict], weights: dict) -> list[dict]:
    """Recompute trend scores for all groups under arbitrary weights (no DB writes)."""
    now = datetime.now(timezone.utc)
    window_7d = now - timedelta(days=7)
    window_28d = now - timedelta(days=28)

    def _parse(iso):
        if not iso:
            return None
        try:
            dt = datetime.fromisoformat(iso)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    groups: dict = defaultdict(list)
    for ev in events:
        key = (ev["competitor"], ev["event_type"] or "unknown", ev.get("cluster_id", -1))
        groups[key].append(ev)

    rows = []
    for (competitor, event_type, _), group in groups.items():
        dates = [_parse(ev["published_at"]) for ev in group]
        dates = [d for d in dates if d]

        count_7d = sum(1 for d in dates if d >= window_7d)
        prev = [ev for ev, d in zip(group, dates) if window_28d <= d < window_7d]

        if not prev:
            mean_p = std_p = 0.0
        else:
            weekly = []
            for wk in range(4):
                ws = window_28d + timedelta(weeks=wk)
                we = ws + timedelta(weeks=1)
                weekly.append(sum(1 for ev, d in zip(group, dates) if d and ws <= d < we))
            mean_p = sum(weekly) / 4
            variance = sum((w - mean_p) ** 2 for w in weekly) / 4
            std_p = math.sqrt(variance)

        unique_sources = len({ev["source_name"] for ev in group})
        impact_scores = [ev["impact_score"] for ev in group if ev.get("impact_score")]
        avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0.0
        sentiment_scores = [ev["sentiment_score"] for ev in group if ev.get("sentiment_score") is not None]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

        burst_z = (count_7d - mean_p) / (std_p + 1)
        score = (
            weights["burst"] * burst_z
            + weights["sources"] * math.log(1 + unique_sources)
            + weights["impact"] * (avg_impact / 5)
            + weights["sentiment"] * avg_sentiment
        )
        rows.append({
            "competitor": competitor,
            "event_type": event_type,
            "trend_score": score,
            "burst_z": burst_z,
            "unique_sources": unique_sources,
            "avg_impact": avg_impact,
            "avg_sentiment": avg_sentiment,
            "count_7d": count_7d,
        })
    return rows


def run_trend_ablation(events: list[dict], weight_configs: list[dict]) -> "pd.DataFrame":
    """
    Evaluate multiple trend formula weight configurations using proxy quality metrics.

    No hand-labeled data required — three unsupervised proxies:
      spearman_corr       : rank correlation of trend_score with avg_impact (↑ better)
      high_impact_mean_rank: mean rank of groups with avg_impact ≥ 3.0 (↓ better)
      top5_mean_impact    : avg_impact of the 5 highest-scoring trends (↑ better)

    Args:
        events: list of event dicts from get_events_for_trends()
        weight_configs: list of dicts with keys: name, burst, sources, impact, sentiment

    Returns:
        pd.DataFrame with one row per configuration.
    """
    import pandas as pd
    from scipy.stats import spearmanr

    results = []
    for cfg in weight_configs:
        rows = _compute_trend_rows(events, cfg)
        if not rows:
            continue
        df = pd.DataFrame(rows).sort_values("trend_score", ascending=False).reset_index(drop=True)

        corr, _ = spearmanr(df["trend_score"], df["avg_impact"])
        hi = df[df["avg_impact"] >= 3.0]
        hi_mean_rank = float((hi.index.to_numpy() + 1).mean()) if len(hi) else float(len(df))
        top5_impact = df.head(5)["avg_impact"].mean()

        results.append({
            "name": cfg["name"],
            "w_burst": cfg["burst"],
            "w_sources": cfg["sources"],
            "w_impact": cfg["impact"],
            "w_sentiment": cfg["sentiment"],
            "n_groups": len(df),
            "top5_mean_impact": round(top5_impact, 3),
            "spearman_corr": round(float(corr), 3),
            "high_impact_mean_rank": round(hi_mean_rank, 1),
        })

    return pd.DataFrame(results)
