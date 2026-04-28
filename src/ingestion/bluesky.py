"""
Bluesky social listening adapter using the public AT Protocol search API.
No authentication required — uses the public appview endpoint.
API docs: https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
"""
import requests
from datetime import datetime, timezone, timedelta
from src.ingestion.query_planner import BRANDS, build_queries

SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
LOOKBACK_DAYS = 7
MIN_ENGAGEMENT = 2  # likeCount + repostCount
MAX_RESULTS_PER_QUERY = 25
REQUEST_TIMEOUT = 10

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


def _fetch_query(query: str) -> list[dict]:
    """Call the Bluesky search API for one query string."""
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"q": query, "limit": MAX_RESULTS_PER_QUERY},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("posts", [])
    except Exception as e:
        print(f"[Bluesky] Error fetching '{query}': {e}")
        return []


def _parse_post(post: dict, brand: str) -> dict | None:
    """Map a Bluesky post object to the standard item schema."""
    try:
        record = post.get("record", {})
        text = record.get("text", "")
        if not text:
            return None

        indexed_at = post.get("indexedAt", "")
        try:
            published = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
        except Exception:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
        if published < cutoff:
            return None

        like_count = post.get("likeCount", 0)
        repost_count = post.get("repostCount", 0)
        reply_count = post.get("replyCount", 0)
        if like_count + repost_count < MIN_ENGAGEMENT:
            return None

        author = post.get("author", {})
        handle = author.get("handle", "unknown")
        uri = post.get("uri", "")
        # Convert at:// URI to a browsable bsky.app URL
        url = ""
        if uri.startswith("at://"):
            parts = uri[5:].split("/")
            if len(parts) == 3:
                url = f"https://bsky.app/profile/{parts[0]}/post/{parts[2]}"

        engagement_prefix = f"[Likes: {like_count}, Reposts: {repost_count}, Replies: {reply_count}] "

        return {
            "competitor": brand,
            "source_type": "social_media",
            "source_name": f"Bluesky - @{handle}",
            "source_url": url or uri,
            "published_at": published.isoformat(),
            "title": f"Bluesky post by @{handle}",
            "excerpt": engagement_prefix + text[:500],
            "raw_text": text[:2000],
            "original_language": "en",
            "official_source": False,
            "engagement_metrics": {
                "likes": like_count,
                "reposts": repost_count,
                "replies": reply_count,
            },
        }
    except Exception:
        return None


def fetch_all(simple: bool = False) -> list[dict]:
    """
    Fetch Bluesky posts mentioning luxury brands.

    simple=True uses only the brand name query (retry fallback).
    Returns empty list gracefully on network failures.
    """
    mode = "simple" if simple else "full"
    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for brand in BRANDS:
        queries = build_queries(brand, mode=mode)
        brand_count = 0

        for query in queries:
            posts = _fetch_query(query)
            for post in posts:
                item = _parse_post(post, brand)
                if item is None:
                    continue
                # Prefer brand detected from text; skip if no brand match
                detected = _detect_brand(item["raw_text"])
                if detected:
                    item["competitor"] = detected
                url = item["source_url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_items.append(item)
                brand_count += 1

        print(f"[Bluesky] {brand}: {brand_count} posts")

    print(f"[Bluesky] Total: {len(all_items)} items")
    return all_items
