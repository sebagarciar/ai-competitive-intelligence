"""
Official brand website scraper using trafilatura.
Note: Many luxury sites have anti-bot protection (Cloudflare, etc).
Uses cloudscraper to bypass Cloudflare protection.
"""
import cloudscraper
import trafilatura
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Create a cloudscraper session that can bypass Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'darwin',
        'desktop': True
    }
)

BRAND_PAGES = [
    {
        "brand": "Chanel",
        "url": "https://www.chanel.com/us/news/",
        "source_name": "Chanel Official",
    },
    {
        "brand": "Dior",
        "url": "https://www.lvmh.com/news-documents/news/",
        "source_name": "Dior Official (LVMH)",
        "filter_brand": True,  # Filter for Dior-specific content
    },
    {
        "brand": "Gucci",
        "url": "https://www.kering.com/en/news/",
        "source_name": "Gucci Official (Kering)",
        "filter_brand": True,  # Filter for Gucci-specific content
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _extract_links(base_url: str, html: str, brand: str, filter_brand: bool = False) -> list[str]:
    from urllib.parse import urljoin, urlparse
    soup = BeautifulSoup(html, "html.parser")
    links = []
    brand_lower = brand.lower()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text().strip().lower()

        # Make absolute URL
        if not href.startswith("http"):
            href = urljoin(base_url, href)

        # Skip if filter_brand is True and brand not mentioned
        if filter_brand and brand_lower not in (href.lower() + " " + text):
            continue

        # Look for news/article URLs
        if any(keyword in href.lower() for keyword in ["news", "stories", "article", "press", "/en/"]):
            # Make sure it's a valid article URL (has path beyond base)
            parsed = urlparse(href)
            if len(parsed.path.strip("/").split("/")) >= 2:
                links.append(href)

    return list(dict.fromkeys(links))[:30]


def _scrape_article(url: str, brand: str, source_name: str) -> dict | None:
    try:
        # Use cloudscraper to fetch the page
        resp = scraper.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        # Extract text using trafilatura
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
        if not text or len(text) < 100:
            return None

        lines = text.strip().split("\n")
        title = lines[0][:200] if lines else url
        excerpt = " ".join(lines[1:4])[:500]

        return {
            "competitor": brand,
            "source_type": "brand_owned",
            "source_name": source_name,
            "source_url": url,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "excerpt": excerpt,
            "raw_text": text[:2000],
            "original_language": "en",
            "official_source": True,
        }
    except Exception as e:
        # Silently skip articles that fail (many links won't be actual articles)
        return None


def fetch_brand(cfg: dict) -> list[dict]:
    items = []
    try:
        # Use cloudscraper to bypass Cloudflare protection
        resp = scraper.get(cfg["url"], headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        filter_brand = cfg.get("filter_brand", False)
        links = _extract_links(cfg["url"], resp.text, cfg["brand"], filter_brand)
        print(f"[BrandSite] {cfg['brand']}: Found {len(links)} potential article links")
    except Exception as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 403:
            print(f"[BrandSite] {cfg['brand']}: Blocked by anti-bot protection (403) - skipping")
        else:
            print(f"[BrandSite] Error fetching index for {cfg['brand']}: {e}")
        return []

    for link in links[:10]:
        item = _scrape_article(link, cfg["brand"], cfg["source_name"])
        if item:
            items.append(item)
        time.sleep(1)  # Rate limit: wait between article scrapes

    print(f"[BrandSite] {cfg['brand']}: {len(items)} articles")
    return items


def fetch_all() -> list[dict]:
    all_items = []
    for cfg in BRAND_PAGES:
        all_items.extend(fetch_brand(cfg))
        time.sleep(2)  # Rate limit: wait between brands
    return all_items
