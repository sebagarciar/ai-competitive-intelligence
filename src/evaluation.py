"""
Reusable metric functions for evaluating pipeline output quality.

Used by notebooks/evaluation.ipynb; can also be imported in tests.
All functions accept human-provided label lists and return scalar scores.
"""
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
