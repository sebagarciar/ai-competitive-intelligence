"""
GDELT DOC 2.0 API connector.
Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
import requests
import time
from datetime import datetime, timezone
from requests.exceptions import HTTPError

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

BRAND_QUERIES = {
    "Chanel": ["Chanel fashion", "Chanel luxury", "Chanel brand"],
    "Dior": ["Dior fashion", "Dior luxury", "Christian Dior"],
    "Gucci": ["Gucci fashion", "Gucci luxury", "Gucci brand"],
}

SOURCE_PRESTIGE = {
    "voguebusiness.com": 5,
    "businessoffashion.com": 5,
    "wwd.com": 4,
    "ft.com": 4,
    "reuters.com": 4,
    "bloomberg.com": 4,
}


def _prestige(url: str) -> int:
    for domain, score in SOURCE_PRESTIGE.items():
        if domain in url:
            return score
    return 2


def fetch_brand(brand: str, max_records: int = 75) -> list[dict]:
    items = []
    seen_urls: set[str] = set()

    for query in BRAND_QUERIES[brand]:
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "timespan": "30d",
        }
        data = None
        backoff = 10
        for attempt in range(4):
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                break
            except HTTPError as e:
                if resp.status_code == 429:
                    print(f"[GDELT] Rate limited on '{query}', backing off {backoff}s (attempt {attempt+1})")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print(f"[GDELT] Error fetching '{query}': {e}")
                    break
            except Exception as e:
                print(f"[GDELT] Error fetching '{query}': {e}")
                break
        else:
            print(f"[GDELT] Giving up on '{query}' after retries")

        if data is None:
            continue

        time.sleep(5)

        for art in data.get("articles", []):
            url = art.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            published_raw = art.get("seendate", "")
            try:
                published_at = datetime.strptime(published_raw, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                ).isoformat()
            except ValueError:
                published_at = None

            items.append({
                "competitor": brand,
                "source_type": "news_aggregator",
                "source_name": "GDELT",
                "source_url": url,
                "published_at": published_at,
                "title": art.get("title", ""),
                "excerpt": art.get("title", ""),
                "raw_text": art.get("title", ""),
                "original_language": art.get("language", "English").lower()[:2],
                "official_source": False,
            })

    return items


def fetch_all() -> list[dict]:
    all_items = []
    for brand in BRAND_QUERIES:
        brand_items = fetch_brand(brand)
        print(f"[GDELT] {brand}: {len(brand_items)} articles")
        all_items.extend(brand_items)
    return all_items
