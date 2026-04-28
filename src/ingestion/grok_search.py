"""
Grok/xAI adapter for live X (Twitter) data.
Uses the xAI API (OpenAI-compatible) with Grok's built-in X search capability.
Requires XAI_API_KEY in environment. Skips gracefully if not set.
Sign up: https://console.x.ai
"""
import os
import json
import re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from src.ingestion.query_planner import BRANDS, build_queries

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_BASE_URL = "https://api.x.ai/v1"
MODEL = "grok-2-1212"
LOOKBACK_DAYS = 7

SYSTEM_PROMPT = (
    "You are a social media data extraction assistant. "
    "When asked to search X, return ONLY a valid JSON array with no prose, "
    "no markdown fences, no explanation. Each element must have exactly these keys: "
    "text (string), author (string), url (string), date (ISO8601 string), "
    "likes (integer), retweets (integer)."
)

USER_PROMPT_TEMPLATE = (
    "Search X for recent posts from the last 7 days about {brand} luxury fashion. "
    "Focus on consumer opinions, reviews, complaints, and reactions. "
    "Return up to 20 results as a JSON array. "
    "Queries to use: {queries}"
)

BRAND_KEYWORDS = {
    "Chanel": ["chanel", "coco chanel", "virginie viard"],
    "Dior": ["dior", "christian dior", "maria grazia"],
    "Gucci": ["gucci", "sabato de sarno"],
}


def _detect_brand(text: str) -> str | None:
    text_lower = text.lower()
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return brand
    return None


def _call_grok(brand: str, queries: list[str]) -> list[dict]:
    """Call the xAI Grok API and return parsed X posts."""
    try:
        import httpx

        prompt = USER_PROMPT_TEMPLATE.format(
            brand=brand,
            queries=", ".join(f'"{q}"' for q in queries),
        )

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{XAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip any accidental markdown fences
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        return json.loads(content)

    except json.JSONDecodeError as e:
        print(f"[Grok] JSON parse error for {brand}: {e}")
        return []
    except Exception as e:
        print(f"[Grok] API error for {brand}: {e}")
        return []


def _parse_post(post: dict, brand: str) -> dict | None:
    """Map a Grok-returned post dict to the standard item schema."""
    try:
        text = str(post.get("text", "")).strip()
        if not text:
            return None

        author = str(post.get("author", "unknown"))
        url = str(post.get("url", ""))
        likes = int(post.get("likes", 0))
        retweets = int(post.get("retweets", 0))

        date_str = str(post.get("date", ""))
        try:
            published = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            published = datetime.now(timezone.utc)

        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        if published < cutoff:
            return None

        engagement_prefix = f"[Likes: {likes}, Retweets: {retweets}] "

        return {
            "competitor": brand,
            "source_type": "social_media",
            "source_name": f"X - @{author}",
            "source_url": url,
            "published_at": published.isoformat(),
            "title": f"X post by @{author}",
            "excerpt": engagement_prefix + text[:500],
            "raw_text": text[:2000],
            "original_language": "en",
            "official_source": False,
            "engagement_metrics": {
                "likes": likes,
                "retweets": retweets,
            },
        }
    except Exception:
        return None


def fetch_all(simple: bool = False) -> list[dict]:
    """
    Fetch recent X posts about luxury brands via Grok's live X search.
    Returns empty list if XAI_API_KEY is not configured.

    simple=True uses only the brand name query (retry fallback).
    """
    if not XAI_API_KEY:
        print("[Grok] XAI_API_KEY not configured — skipping X search via Grok")
        return []

    # httpx is the HTTP client used here; check it's available
    try:
        import httpx  # noqa: F401
    except ImportError:
        print("[Grok] httpx not installed. Run: pip install httpx")
        return []

    mode = "simple" if simple else "full"
    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for brand in BRANDS:
        queries = build_queries(brand, mode=mode)
        raw_posts = _call_grok(brand, queries)
        brand_count = 0

        for post in raw_posts:
            if not isinstance(post, dict):
                continue
            item = _parse_post(post, brand)
            if item is None:
                continue
            detected = _detect_brand(item["raw_text"])
            if detected:
                item["competitor"] = detected
            url = item["source_url"]
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            all_items.append(item)
            brand_count += 1

        print(f"[Grok/X] {brand}: {brand_count} posts")

    print(f"[Grok/X] Total: {len(all_items)} items")
    return all_items
