"""
RSS feed connector for fashion/luxury media.
"""
import feedparser
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Set User-Agent for RSS feeds
feedparser.USER_AGENT = "Mozilla/5.0 (compatible; LuxuryFashionBot/1.0)"

FEEDS = [
    {
        "url": "https://wwd.com/feed/",
        "source_name": "WWD",
        "source_type": "fashion_media",
    },
    {
        "url": "https://hypebae.com/feed",
        "source_name": "Hypebae",
        "source_type": "fashion_media",
    },
    {
        "url": "https://hypebeast.com/feed",
        "source_name": "Hypebeast",
        "source_type": "fashion_media",
    },
    {
        "url": "https://www.highsnobiety.com/feed/",
        "source_name": "Highsnobiety",
        "source_type": "fashion_media",
    },
    {
        "url": "https://www.vogue.com/feed/rss",
        "source_name": "Vogue",
        "source_type": "fashion_media",
    },
    {
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "source_name": "Bloomberg Markets",
        "source_type": "news_wire",
    },
    {
        "url": "https://www.elle.com/rss/all.xml/",
        "source_name": "Elle",
        "source_type": "fashion_media",
    },
    {
        "url": "https://www.dezeen.com/feed/",
        "source_name": "Dezeen",
        "source_type": "fashion_media",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/FashionandStyle.xml",
        "source_name": "NY Times Fashion",
        "source_type": "fashion_media",
    },
]

BRANDS = ["Chanel", "Dior", "Gucci"]
BRAND_KEYWORDS = {
    "Chanel": ["chanel", "gabrielle", "karl lagerfeld", "virginie viard"],
    "Dior": ["dior", "christian dior", "maria grazia chiuri", "kim jones"],
    "Gucci": ["gucci", "sabato de sarno", "kering"],
}


def _detect_brand(text: str) -> str | None:
    text_lower = text.lower()
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return brand
    return None


def _parse_date(entry) -> str | None:
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    return None


def fetch_feed(feed_cfg: dict) -> list[dict]:
    parsed = feedparser.parse(feed_cfg["url"])
    items = []

    for entry in parsed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = f"{title} {summary}"

        brand = _detect_brand(combined)
        if not brand:
            continue

        url = entry.get("link", "")
        if not url:
            continue

        items.append({
            "competitor": brand,
            "source_type": feed_cfg["source_type"],
            "source_name": feed_cfg["source_name"],
            "source_url": url,
            "published_at": _parse_date(entry),
            "title": title,
            "excerpt": summary[:500] if summary else title,
            "raw_text": summary or title,
            "original_language": "en",
            "official_source": False,
        })

    return items


def fetch_all() -> list[dict]:
    all_items = []
    for feed_cfg in FEEDS:
        try:
            items = fetch_feed(feed_cfg)
            print(f"[RSS] {feed_cfg['source_name']}: {len(items)} brand-relevant articles")
            all_items.extend(items)
        except Exception as e:
            print(f"[RSS] Error fetching {feed_cfg['source_name']}: {e}")
        time.sleep(1)  # Rate limit: wait between feeds
    return all_items
