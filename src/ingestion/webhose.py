"""
Webhose.io API connector for luxury brand news aggregation.
Fetches articles with social engagement metrics.
Docs: https://docs.webhose.io/docs/getting-started
"""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WEBHOSE_API_KEY")
BASE_URL = "https://webhose.io/filterWebContent"

# Brand-specific queries
BRAND_QUERIES = {
    "Chanel": '(Chanel OR "Virginie Viard" OR "Karl Lagerfeld") language:english site_type:news',
    "Dior": '(Dior OR "Christian Dior" OR "Maria Grazia Chiuri" OR "Kim Jones") language:english site_type:news',
    "Gucci": '(Gucci OR "Sabato De Sarno" OR Kering) language:english site_type:news',
}

# High-quality fashion domains (optional filter)
PREFERRED_DOMAINS = [
    "voguebusiness.com",
    "businessoffashion.com",
    "wwd.com",
    "ft.com",
    "reuters.com",
    "bloomberg.com",
]

LOOKBACK_DAYS = 30  # Match GDELT's 30-day window
MAX_RESULTS = 100   # Max per request


def _detect_brand(text: str) -> str | None:
    """Detect brand from article text using keyword matching."""
    text_lower = text.lower()
    keywords = {
        "Chanel": ["chanel", "gabrielle", "virginie viard"],
        "Dior": ["dior", "christian dior", "maria grazia chiuri"],
        "Gucci": ["gucci", "sabato de sarno", "kering"],
    }
    for brand, kws in keywords.items():
        if any(kw in text_lower for kw in kws):
            return brand
    return None


def _parse_social_metrics(thread: dict) -> str:
    """Extract social engagement metrics as prefix string."""
    shares = thread.get("social", {})
    facebook_shares = shares.get("facebook", {}).get("shares", 0)
    linkedin_shares = shares.get("linkedin", {}).get("shares", 0)
    total_shares = facebook_shares + linkedin_shares

    if total_shares > 0:
        return f"[Shares: {total_shares:,}] "
    return ""


def fetch_brand(brand: str) -> list[dict]:
    """Fetch articles for a specific brand."""
    if not API_KEY:
        return []

    # Calculate timestamp for 30 days ago (Unix timestamp in milliseconds)
    ts_start = int((datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).timestamp() * 1000)

    params = {
        "token": API_KEY,
        "q": BRAND_QUERIES[brand],
        "ts": ts_start,
        "size": MAX_RESULTS,
        "sort": "crawled:desc",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            print(f"[Webhose] Quota exceeded or invalid API key for {brand}")
        elif e.response.status_code == 401:
            print(f"[Webhose] Authentication failed. Check WEBHOSE_API_KEY")
        else:
            print(f"[Webhose] HTTP error {e.response.status_code} for {brand}")
        return []
    except Exception as e:
        print(f"[Webhose] Error fetching {brand}: {e}")
        return []

    items = []
    for post in data.get("posts", []):
        url = post.get("url", "")
        if not url:
            continue

        title = post.get("title", "")
        text = post.get("text", "")

        # Verify brand relevance (API may return false positives)
        if not _detect_brand(f"{title} {text}"):
            continue

        # Parse social metrics
        social_prefix = _parse_social_metrics(post.get("thread", {}))

        # Parse published date
        published_raw = post.get("published", "")
        try:
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).isoformat()
        except Exception:
            print(f"[Webhose] Unparseable date {published_raw!r} — setting published_at=None")
            published_at = None

        items.append({
            "competitor": brand,
            "source_type": "news_aggregator",
            "source_name": "Webhose",
            "source_url": url,
            "published_at": published_at,
            "title": title,
            "excerpt": social_prefix + text[:500],
            "raw_text": text[:2000],
            "original_language": post.get("language", "english")[:2],
            "official_source": False,
        })

    return items


def fetch_all() -> list[dict]:
    """
    Fetch articles for all brands.
    Returns empty list if API key not configured.
    """
    if not API_KEY:
        print("[Webhose] WEBHOSE_API_KEY not configured. Skipping Webhose ingestion.")
        print("[Webhose] To enable: Get API key from https://webhose.io")
        return []

    all_items = []
    for brand in BRAND_QUERIES.keys():
        items = fetch_brand(brand)
        print(f"[Webhose] {brand}: {len(items)} articles")
        all_items.extend(items)

    return all_items
