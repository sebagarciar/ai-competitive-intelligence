"""
Event extraction without an LLM API.

Two-step approach:
  1. Keyword scoring — fast, deterministic, covers ~80% of cases
  2. Zero-shot classification (facebook/bart-large-mnli) — used when keyword
     confidence is below threshold; loaded lazily to avoid startup cost
"""
import re
from functools import lru_cache
from typing import Optional
from src.config import KEYWORD_CONFIDENCE_THRESHOLD

# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

EVENT_KEYWORDS: dict[str, list[str]] = {
    "collection_launch": [
        "collection", "debut", "launch", "show", "runway", "fashion week",
        "couture", "ready-to-wear", "rtw", "spring", "summer", "fall", "winter",
        "cruise", "resort", "presented", "unveiled", "preview",
    ],
    "campaign_or_collaboration": [
        "campaign", "collaboration", "collab", "partnership", "ambassador",
        "capsule", "limited edition", "co-design", "joint", "co-branded",
    ],
    "pricing_or_exclusivity": [
        "price", "pricing", "exclusive", "exclusivity", "increase", "hike",
        "premium", "cost", "luxury tier", "price point", "more expensive",
    ],
    "geographic_expansion": [
        "flagship", "store opening", "expansion", "boutique", "new market",
        "opens in", "enters", "pop-up", "retail", "china", "asia", "middle east",
        "united states", "europe", "india", "brazil",
    ],
    "creative_direction": [
        "creative director", "designer", "artistic director", "appointed",
        "hired", "replaced", "succession", "new head", "creative vision",
        "aesthetic", "direction change",
    ],
    "sustainability_or_sourcing": [
        "sustainability", "sustainable", "circular", "recycled", "organic",
        "carbon", "emissions", "eco", "ethical sourcing", "supply chain",
        "fair trade", "biodiversity", "net zero",
    ],
    "celebrity_or_influencer_alignment": [
        "celebrity", "influencer", "muse", "face of", "spokesperson",
        "brand ambassador", "wore", "spotted wearing", "dressed by",
        "red carpet", "met gala", "oscar", "grammy",
    ],
    "reputational_issue": [
        "controversy", "scandal", "backlash", "criticism", "accused",
        "protest", "boycott", "apology", "lawsuit", "cultural appropriation",
        "offensive", "recalled",
    ],
}

BUSINESS_FUNCTION_MAP: dict[str, str] = {
    "collection_launch": "product",
    "campaign_or_collaboration": "marketing",
    "pricing_or_exclusivity": "commercial",
    "geographic_expansion": "commercial",
    "creative_direction": "leadership",
    "sustainability_or_sourcing": "operations",
    "celebrity_or_influencer_alignment": "marketing",
    "reputational_issue": "corporate",
}

SOURCE_PRESTIGE_SCORES: dict[str, int] = {
    "Vogue Business": 5,
    "Business of Fashion": 5,
    "WWD": 4,
    "Financial Times": 4,
    "Chanel Official": 5,
    "Dior Official": 5,
    "Gucci Official": 5,
    "GDELT": 2,
}

ZS_MODEL_NAME = "cross-encoder/nli-MiniLM2-L6-H768"  # lighter than bart-large-mnli


# ---------------------------------------------------------------------------
# Keyword scorer
# ---------------------------------------------------------------------------

def _keyword_score(text: str) -> dict[str, float]:
    text_lower = text.lower()
    scores: dict[str, float] = {}
    for event_type, keywords in EVENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        scores[event_type] = hits / len(keywords)
    return scores


def _top_event(scores: dict[str, float]) -> tuple[str, float]:
    best = max(scores, key=lambda k: scores[k])
    return best, scores[best]


def _evidence_snippet(text: str, event_type: str) -> str:
    keywords = EVENT_KEYWORDS.get(event_type, [])
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sent in sentences:
        sent_lower = sent.lower()
        if any(kw in sent_lower for kw in keywords):
            return sent[:300]
    return text[:300]


def _relevance_score(text: str, brand: str) -> float:
    count = text.lower().count(brand.lower())
    if count >= 3:
        return 5.0
    if count == 2:
        return 4.0
    if count == 1:
        return 3.0
    return 2.0


def _impact_score(source_name: str, keyword_score: float, official: bool) -> float:
    prestige = SOURCE_PRESTIGE_SCORES.get(source_name, 2)
    base = prestige * 0.6 + keyword_score * 10 * 0.4
    score = max(1.0, min(5.0, base))
    if official:
        score = min(5.0, score + 0.5)
    return round(score, 1)


# ---------------------------------------------------------------------------
# Zero-shot fallback (lazy-loaded)
# ---------------------------------------------------------------------------

_zs_pipeline = None


@lru_cache(maxsize=1)
def _get_zs_pipeline():
    from transformers import pipeline as hf_pipeline
    print(f"[Extractor] Loading zero-shot model {ZS_MODEL_NAME}...")
    return hf_pipeline("zero-shot-classification", model=ZS_MODEL_NAME)


def _zero_shot_classify(text: str) -> tuple[str, float]:
    zs = _get_zs_pipeline()
    labels = list(EVENT_KEYWORDS.keys())
    result = zs(text[:512], candidate_labels=labels)
    return result["labels"][0], result["scores"][0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_event(item: dict, use_zero_shot: bool = False) -> dict:
    text = item.get("translated_text") or item.get("raw_text") or item.get("title") or ""
    brand = item.get("competitor", "")
    source_name = item.get("source_name", "")
    official = bool(item.get("official_source", False))
    item_id = item.get("item_id", "")

    kw_scores = _keyword_score(text)
    event_type, kw_conf = _top_event(kw_scores)

    if use_zero_shot and kw_conf < KEYWORD_CONFIDENCE_THRESHOLD:
        try:
            event_type, confidence = _zero_shot_classify(text)
        except Exception as e:
            print(f"[Extractor] Zero-shot failed: {e}")
            confidence = kw_conf
    else:
        confidence = min(1.0, kw_conf * 5)  # scale to [0,1] rough approximation

    # Fallback: if no keyword hit at all, mark unknown
    if kw_conf == 0.0:
        event_type = "collection_launch"
        confidence = 0.1

    summary_text = item.get("translated_text") or item.get("excerpt") or ""
    sentences = re.split(r"(?<=[.!?])\s+", summary_text)
    summary = " ".join(sentences[:2])[:400]

    return {
        "item_id": item_id,
        "competitor": brand,
        "event_type": event_type,
        "business_function": BUSINESS_FUNCTION_MAP.get(event_type, "other"),
        "relevance_score": _relevance_score(text, brand),
        "impact_score": _impact_score(source_name, kw_conf, official),
        "summary": summary,
        "evidence_snippet": _evidence_snippet(text, event_type),
        "confidence_score": round(confidence, 3),
        "duplicate_group_id": item.get("duplicate_group_id"),
    }
