"""
Reddit social listening connector using PRAW (official Reddit API).
Monitors fashion subreddits for brand mentions and consumer sentiment.
Also searches Reddit by keyword queries from the query planner.
Docs: https://praw.readthedocs.io/
"""
import os
import praw
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from src.ingestion.query_planner import BRANDS, build_queries

load_dotenv()

# Reddit API credentials (get from https://www.reddit.com/prefs/apps)
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "luxury-brand-intelligence:v1.0")

# Fashion subreddits to monitor
FASHION_SUBREDDITS = [
    "luxury",
    "luxuryfashion",
    "fashion",
    "femalefashionadvice",
    "malefashionadvice",
    "handbags",
    "designerbags",
    "Chanel",  # Brand-specific
    "Dior",
    "Gucci",
]

# Brand keywords to filter posts/comments
BRAND_KEYWORDS = {
    "Chanel": ["chanel", "coco", "gabrielle", "karl lagerfeld", "virginie viard"],
    "Dior": ["dior", "christian dior", "maria grazia", "sauvage"],
    "Gucci": ["gucci", "sabato de sarno", "alessandro michele", "kering"],
}

LOOKBACK_DAYS = 7  # How far back to search
MIN_UPVOTES = 5  # Filter low-engagement posts
MAX_POSTS_PER_SUBREDDIT = 50  # API quota management
MAX_SEARCH_RESULTS = 25  # Per keyword query via Reddit search


def _detect_brand(text: str) -> str | None:
    """Detect which brand is mentioned in the text."""
    text_lower = text.lower()
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return brand
    return None


def _fetch_subreddit_posts(reddit, subreddit_name: str) -> list[dict]:
    """Fetch recent posts from a subreddit that mention luxury brands."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        items = []

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

        # Fetch hot + new posts to capture trending and recent
        posts = list(subreddit.hot(limit=MAX_POSTS_PER_SUBREDDIT // 2))
        posts.extend(list(subreddit.new(limit=MAX_POSTS_PER_SUBREDDIT // 2)))

        for post in posts:
            # Filter by engagement and recency
            if post.score < MIN_UPVOTES:
                continue

            created_utc = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if created_utc < cutoff_date:
                continue

            # Check if post mentions any brand
            text = f"{post.title} {post.selftext}"
            brand = _detect_brand(text)
            if not brand:
                continue

            # Build engagement metrics prefix
            engagement_prefix = (
                f"[Upvotes: {post.score}, Comments: {post.num_comments}, "
                f"Upvote Ratio: {post.upvote_ratio:.0%}] "
            )

            items.append({
                "competitor": brand,
                "source_type": "social_media",
                "source_name": f"Reddit - r/{subreddit_name}",
                "source_url": f"https://reddit.com{post.permalink}",
                "published_at": created_utc.isoformat(),
                "title": post.title,
                "excerpt": engagement_prefix + (post.selftext[:500] if post.selftext else post.title),
                "raw_text": f"{post.title}\n\n{post.selftext[:2000]}",
                "original_language": "en",
                "official_source": False,
                # Social engagement metadata (stored in excerpt for now)
                "engagement_metrics": {
                    "upvotes": post.score,
                    "comments": post.num_comments,
                    "upvote_ratio": post.upvote_ratio,
                }
            })

        return items

    except Exception as e:
        print(f"[Reddit] Error fetching r/{subreddit_name}: {e}")
        return []


def _fetch_comments_from_post(post, brand: str, max_comments: int = 10) -> list[dict]:
    """Extract top comments from a post for deeper sentiment analysis."""
    items = []

    try:
        # Flatten comment tree and sort by score
        post.comments.replace_more(limit=0)  # Don't load "load more comments"
        comments = sorted(post.comments.list(), key=lambda c: c.score, reverse=True)

        for comment in comments[:max_comments]:
            if comment.score < MIN_UPVOTES:
                continue

            if len(comment.body) < 20:  # Skip very short comments
                continue

            created_utc = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)

            engagement_prefix = f"[Upvotes: {comment.score}] "

            items.append({
                "competitor": brand,
                "source_type": "social_media",
                "source_name": f"Reddit - r/{post.subreddit.display_name} (comment)",
                "source_url": f"https://reddit.com{comment.permalink}",
                "published_at": created_utc.isoformat(),
                "title": f"Comment on: {post.title[:100]}",
                "excerpt": engagement_prefix + comment.body[:500],
                "raw_text": comment.body[:2000],
                "original_language": "en",
                "official_source": False,
                "engagement_metrics": {
                    "upvotes": comment.score,
                }
            })

        return items

    except Exception as e:
        print(f"[Reddit] Error fetching comments: {e}")
        return []


def _search_reddit_by_queries(reddit, queries: list[str]) -> list[dict]:
    """
    Search reddit.subreddit("all") for each query string.
    Complements subreddit browsing with keyword-driven discovery.
    """
    items = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for query in queries:
        try:
            results = reddit.subreddit("all").search(
                query,
                sort="new",
                time_filter="week",
                limit=MAX_SEARCH_RESULTS,
            )
            for post in results:
                if post.score < MIN_UPVOTES:
                    continue
                created_utc = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if created_utc < cutoff_date:
                    continue
                text = f"{post.title} {post.selftext}"
                brand = _detect_brand(text)
                if not brand:
                    continue
                engagement_prefix = (
                    f"[Upvotes: {post.score}, Comments: {post.num_comments}, "
                    f"Upvote Ratio: {post.upvote_ratio:.0%}] "
                )
                items.append({
                    "competitor": brand,
                    "source_type": "social_media",
                    "source_name": f"Reddit - r/{post.subreddit.display_name}",
                    "source_url": f"https://reddit.com{post.permalink}",
                    "published_at": created_utc.isoformat(),
                    "title": post.title,
                    "excerpt": engagement_prefix + (post.selftext[:500] if post.selftext else post.title),
                    "raw_text": f"{post.title}\n\n{post.selftext[:2000]}",
                    "original_language": "en",
                    "official_source": False,
                    "engagement_metrics": {
                        "upvotes": post.score,
                        "comments": post.num_comments,
                        "upvote_ratio": post.upvote_ratio,
                    },
                })
        except Exception as e:
            print(f"[Reddit] Search error for '{query}': {e}")

    return items


def fetch_all(simple: bool = False) -> list[dict]:
    """
    Fetch posts from fashion subreddits and via keyword search for luxury brands.
    simple=True uses only brand name queries (retry fallback).
    Returns empty list if Reddit API credentials not configured.
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        print("[Reddit] REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not configured.")
        print("[Reddit] To enable: Create app at https://www.reddit.com/prefs/apps")
        print("[Reddit] Set as 'script' type, get client_id and client_secret")
        return []

    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT,
        )

        # Test connection
        reddit.user.me()  # Will fail if credentials invalid
    except Exception as e:
        print(f"[Reddit] Authentication failed: {e}")
        print("[Reddit] Check your REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
        return []

    all_items = []
    seen_urls: set[str] = set()

    # Subreddit browsing (existing approach)
    for subreddit_name in FASHION_SUBREDDITS:
        posts = _fetch_subreddit_posts(reddit, subreddit_name)
        print(f"[Reddit] r/{subreddit_name}: {len(posts)} posts")
        for item in posts:
            url = item.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)

    # Keyword search across all of Reddit using query planner
    mode = "simple" if simple else "full"
    all_queries: list[str] = []
    for brand in BRANDS:
        all_queries.extend(build_queries(brand, mode=mode))

    search_items = _search_reddit_by_queries(reddit, all_queries)
    search_new = 0
    for item in search_items:
        url = item.get("source_url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            all_items.append(item)
            search_new += 1
    print(f"[Reddit] Keyword search: {search_new} additional posts")

    print(f"[Reddit] Total: {len(all_items)} items")
    return all_items
