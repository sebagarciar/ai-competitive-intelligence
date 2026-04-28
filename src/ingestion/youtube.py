"""
YouTube Data API v3 connector for luxury brand video content.
Fetches videos from official brand channels and keyword searches.
Docs: https://developers.google.com/youtube/v3/docs
"""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Official brand channels
OFFICIAL_CHANNELS = {
    "Chanel": "UCqVEHtQoXHmUCfJ-9smpTSg",
    "Dior": "UCKHxD-PzncQlDNPhK9WKFEQ",
    "Gucci": "UC7usJ0h-4l26mlMgLSbPcFA",
}

# Fashion media channels to monitor (optional - disabled by default to conserve quota)
MEDIA_CHANNELS = {
    "Vogue": "UCnr1s6JWQIJZfTfsEi3p1EQ",
    "Business of Fashion": "UCIxD8-vJZH2lRLRl9FvQKxQ",
}

# Brand keyword searches
BRAND_KEYWORDS = {
    "Chanel": ["Chanel fashion", "Chanel runway", "Chanel collection"],
    "Dior": ["Dior fashion", "Dior runway", "Christian Dior"],
    "Gucci": ["Gucci fashion", "Gucci runway", "Gucci collection"],
}

MIN_VIEW_THRESHOLD = 1000  # Filter low-engagement content
LOOKBACK_DAYS = 7  # Avoid re-ingesting old videos


def _detect_brand(text: str) -> str | None:
    """Detect brand from title/description using keyword matching."""
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


def _fetch_channel_videos(channel_id: str, brand: str, is_official: bool) -> list[dict]:
    """Fetch recent videos from a specific channel."""
    if not API_KEY:
        return []

    published_after = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()

    # Search endpoint (100 units per request)
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "type": "video",
        "maxResults": 20,
        "publishedAfter": published_after,
        "order": "date",
        "key": API_KEY,
    }

    try:
        resp = requests.get(f"{BASE_URL}/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            print(f"[YouTube] Quota exceeded or invalid key for channel {brand}")
        else:
            print(f"[YouTube] HTTP error {e.response.status_code} for channel {brand}")
        return []
    except Exception as e:
        print(f"[YouTube] Error fetching channel {brand}: {e}")
        return []

    items = []
    video_ids = [item["id"]["videoId"] for item in data.get("items", [])]

    # Get video statistics (1 unit per call, batched up to 50 videos)
    if video_ids:
        stats = _fetch_video_statistics(video_ids)
    else:
        stats = {}

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        # Filter low-engagement videos
        view_count = stats.get(video_id, {}).get("viewCount", 0)
        if view_count < MIN_VIEW_THRESHOLD:
            continue

        title = snippet.get("title", "")
        description = snippet.get("description", "")

        # Build engagement prefix
        likes = stats.get(video_id, {}).get("likeCount", 0)
        engagement_prefix = f"[Views: {view_count:,}, Likes: {likes:,}] "

        items.append({
            "competitor": brand,
            "source_type": "video_content",
            "source_name": f"YouTube - {snippet.get('channelTitle', 'Unknown')}",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": snippet.get("publishedAt"),
            "title": title,
            "excerpt": engagement_prefix + description[:500],
            "raw_text": f"{title}\n\n{description[:2000]}",
            "original_language": "en",  # Could enhance with language detection
            "official_source": is_official,
        })

    return items


def _fetch_video_statistics(video_ids: list[str]) -> dict:
    """Fetch view counts and engagement metrics for videos (1 unit per request)."""
    if not API_KEY:
        return {}

    params = {
        "part": "statistics",
        "id": ",".join(video_ids[:50]),  # Max 50 per request
        "key": API_KEY,
    }

    try:
        resp = requests.get(f"{BASE_URL}/videos", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[YouTube] Error fetching statistics: {e}")
        return {}

    stats = {}
    for item in data.get("items", []):
        video_id = item["id"]
        statistics = item.get("statistics", {})
        stats[video_id] = {
            "viewCount": int(statistics.get("viewCount", 0)),
            "likeCount": int(statistics.get("likeCount", 0)),
        }

    return stats


def _search_keywords(brand: str) -> list[dict]:
    """Search for brand mentions in video titles/descriptions."""
    if not API_KEY:
        return []

    items = []
    published_after = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()

    # Limit to 2 queries per brand to conserve quota
    for query in BRAND_KEYWORDS.get(brand, [])[:2]:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
            "publishedAfter": published_after,
            "order": "relevance",
            "key": API_KEY,
        }

        try:
            resp = requests.get(f"{BASE_URL}/search", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[YouTube] Error searching '{query}': {e}")
            continue

        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]

            title = snippet.get("title", "")
            description = snippet.get("description", "")

            # Verify brand relevance
            if not _detect_brand(f"{title} {description}"):
                continue

            items.append({
                "competitor": brand,
                "source_type": "video_content",
                "source_name": f"YouTube - {snippet.get('channelTitle', 'Search')}",
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": snippet.get("publishedAt"),
                "title": title,
                "excerpt": description[:500],
                "raw_text": f"{title}\n\n{description[:2000]}",
                "original_language": "en",
                "official_source": False,
            })

    return items


def fetch_all() -> list[dict]:
    """
    Fetch videos from official channels and keyword searches.
    Returns empty list if API key not configured.
    """
    if not API_KEY:
        print("[YouTube] YOUTUBE_API_KEY not configured. Skipping YouTube ingestion.")
        print("[YouTube] To enable: Get API key from https://console.cloud.google.com/apis/credentials")
        return []

    all_items = []

    # Fetch official channels (high value, low quota cost)
    for brand, channel_id in OFFICIAL_CHANNELS.items():
        items = _fetch_channel_videos(channel_id, brand, is_official=True)
        print(f"[YouTube] {brand} official: {len(items)} videos")
        all_items.extend(items)

    # Optional: Fetch from media channels
    # (Commented out to conserve quota - enable if needed)
    # for channel_name, channel_id in MEDIA_CHANNELS.items():
    #     for brand in ["Chanel", "Dior", "Gucci"]:
    #         items = _fetch_channel_videos(channel_id, brand, is_official=False)
    #         all_items.extend(items)

    # Keyword searches (supplement official content)
    for brand in ["Chanel", "Dior", "Gucci"]:
        items = _search_keywords(brand)
        print(f"[YouTube] {brand} search: {len(items)} videos")
        all_items.extend(items)

    return all_items
