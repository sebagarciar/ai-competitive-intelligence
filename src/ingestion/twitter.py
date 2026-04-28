"""
Twitter/X social listening using ntscraper (unofficial scraping).
WARNING: This is fragile and may break if Twitter changes their site structure.
For production use, consider Twitter API (paid) or monitor status at https://github.com/bocchilorenzo/ntscraper
"""
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# Set to True to enable Twitter scraping (disabled by default due to fragility)
TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "false").lower() == "true"

BRAND_ACCOUNTS = {
    "Chanel": ["CHANEL", "chanelofficial"],
    "Dior": ["Dior", "DiorBeauty"],
    "Gucci": ["gucci"],
}

BRAND_HASHTAGS = {
    "Chanel": ["#Chanel", "#ChanelFashion"],
    "Dior": ["#Dior", "#DiorFashion"],
    "Gucci": ["#Gucci", "#GucciFashion"],
}

# Fashion influencer accounts to monitor
INFLUENCER_ACCOUNTS = [
    "voguemagazine",
    "CFDA",
    "SusieLau",
    "BryanBoycom",
    "TheCutsleeve",
]

LOOKBACK_DAYS = 3  # Twitter moves fast, focus on recent
MIN_LIKES = 100  # Filter low-engagement tweets
MAX_TWEETS_PER_QUERY = 50


def _detect_brand(text: str) -> str | None:
    """Detect brand from tweet text."""
    text_lower = text.lower()
    keywords = {
        "Chanel": ["chanel", "#chanel"],
        "Dior": ["dior", "#dior"],
        "Gucci": ["gucci", "#gucci"],
    }
    for brand, kws in keywords.items():
        if any(kw in text_lower for kw in kws):
            return brand
    return None


def _scrape_tweets(query: str, limit: int = MAX_TWEETS_PER_QUERY) -> list[dict]:
    """Scrape tweets for a given query using ntscraper."""
    try:
        from ntscraper import Nitter

        scraper = Nitter(log_level=1, skip_instance_check=False)

        # Get tweets from the query
        tweets = scraper.get_tweets(query, mode="term", number=limit)

        if not tweets or "tweets" not in tweets:
            return []

        items = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

        for tweet in tweets["tweets"]:
            # Parse date
            try:
                date_str = tweet.get("date", "")
                # ntscraper returns dates in various formats, try parsing
                tweet_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                continue

            if tweet_date < cutoff_date:
                continue

            # Filter by engagement
            likes = tweet.get("stats", {}).get("likes", 0)
            if likes < MIN_LIKES:
                continue

            text = tweet.get("text", "")
            brand = _detect_brand(text)
            if not brand:
                continue

            # Check if it's from an influencer
            username = tweet.get("user", {}).get("username", "")
            is_influencer = username.lower() in [acc.lower() for acc in INFLUENCER_ACCOUNTS]

            # Build engagement metrics
            stats = tweet.get("stats", {})
            retweets = stats.get("retweets", 0)
            quotes = stats.get("quotes", 0)
            replies = stats.get("replies", 0)

            engagement_prefix = (
                f"[Likes: {likes}, Retweets: {retweets}, Replies: {replies}] "
            )
            if is_influencer:
                engagement_prefix = f"[INFLUENCER @{username}] " + engagement_prefix

            items.append({
                "competitor": brand,
                "source_type": "social_media",
                "source_name": f"Twitter/X - @{username}",
                "source_url": tweet.get("link", ""),
                "published_at": tweet_date.isoformat(),
                "title": f"Tweet by @{username}",
                "excerpt": engagement_prefix + text[:500],
                "raw_text": text[:2000],
                "original_language": "en",  # Could enhance with language detection
                "official_source": username.lower() in [acc.lower() for accs in BRAND_ACCOUNTS.values() for acc in accs],
                "engagement_metrics": {
                    "likes": likes,
                    "retweets": retweets,
                    "replies": replies,
                    "quotes": quotes,
                    "is_influencer": is_influencer,
                }
            })

        return items

    except ImportError:
        print("[Twitter] ntscraper not installed. Run: pip install ntscraper")
        return []
    except Exception as e:
        print(f"[Twitter] Error scraping '{query}': {e}")
        print("[Twitter] Note: ntscraper is fragile and may break. Consider disabling.")
        return []


def fetch_all() -> list[dict]:
    """
    Scrape tweets mentioning luxury brands, from brand accounts, and influencers.
    Returns empty list if TWITTER_ENABLED=false or scraping fails.
    """
    if not TWITTER_ENABLED:
        print("[Twitter] Disabled (set TWITTER_ENABLED=true in .env to enable)")
        print("[Twitter] WARNING: Twitter scraping is fragile and may break")
        return []

    all_items = []

    # Search by hashtags (most reliable)
    for brand, hashtags in BRAND_HASHTAGS.items():
        for hashtag in hashtags:
            tweets = _scrape_tweets(hashtag, limit=MAX_TWEETS_PER_QUERY)
            print(f"[Twitter] {hashtag}: {len(tweets)} tweets")
            all_items.extend(tweets)

    # Monitor influencer accounts
    for account in INFLUENCER_ACCOUNTS[:3]:  # Limit to conserve scraping
        tweets = _scrape_tweets(f"from:{account}", limit=20)
        print(f"[Twitter] @{account}: {len(tweets)} tweets")
        all_items.extend(tweets)

    print(f"[Twitter] Total: {len(all_items)} tweets")
    return all_items
