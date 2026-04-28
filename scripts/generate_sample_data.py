"""
Generate realistic sample data for testing the full pipeline.
Populates the database with synthetic articles across all brands and event types.

Usage:
    python scripts/generate_sample_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from datetime import datetime, timezone, timedelta
import random
from src.db import init_db, insert_item, get_connection

# Sample data templates
SAMPLE_ARTICLES = [
    # Chanel
    {
        "competitor": "Chanel",
        "event_type": "collection_launch",
        "title": "Chanel Unveils Spring 2026 Haute Couture Collection in Paris",
        "excerpt": "Karl Lagerfeld's successor presents a stunning new couture collection featuring innovative textile techniques and the house's signature tweed reimagined for modern sensibilities.",
        "source_name": "Vogue Business",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.5,
    },
    {
        "competitor": "Chanel",
        "event_type": "pricing_or_exclusivity",
        "title": "Chanel Raises Prices on Classic Flap Bags by 12% Globally",
        "excerpt": "The French luxury house has increased prices across its iconic handbag line, marking the third price adjustment this year as demand continues to outpace supply.",
        "source_name": "Business of Fashion",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.8,
    },
    {
        "competitor": "Chanel",
        "event_type": "geographic_expansion",
        "title": "Chanel Opens Flagship Boutique in Mumbai's Jio World Plaza",
        "excerpt": "The luxury brand enters India with a 5,000 square foot flagship showcasing ready-to-wear, accessories, and fine jewelry as it targets high-net-worth individuals in emerging markets.",
        "source_name": "WWD",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.2,
    },
    {
        "competitor": "Chanel",
        "event_type": "celebrity_or_influencer_alignment",
        "title": "Margot Robbie Named New Face of Chanel No. 5 Campaign",
        "excerpt": "The Oscar-nominated actress joins the house as global ambassador for its signature fragrance, appearing in campaigns shot by renowned photographer Patrick Demarchelier.",
        "source_name": "Vogue Business",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.8,
    },

    # Dior
    {
        "competitor": "Dior",
        "event_type": "campaign_or_collaboration",
        "title": "Dior and Birkenstock Unveil Limited Edition Sandal Collaboration",
        "excerpt": "Maria Grazia Chiuri collaborates with the German comfort brand on a luxury reinterpretation of the Boston clog, featuring hand-embroidered canvas and premium leather.",
        "source_name": "Business of Fashion",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.6,
    },
    {
        "competitor": "Dior",
        "event_type": "sustainability_or_sourcing",
        "title": "Dior Commits to 100% Traceable Cashmere by 2027",
        "excerpt": "The LVMH-owned brand announces partnership with Mongolian herders to ensure ethical sourcing and complete supply chain transparency for all cashmere products.",
        "source_name": "Financial Times",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.9,
    },
    {
        "competitor": "Dior",
        "event_type": "collection_launch",
        "title": "Dior Men's Fall 2026 Show Features Futuristic Tailoring",
        "excerpt": "Kim Jones presents a collection blending traditional French tailoring with technical fabrics and deconstructed silhouettes at Paris Fashion Week.",
        "source_name": "Vogue Business",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.1,
    },
    {
        "competitor": "Dior",
        "event_type": "creative_direction",
        "title": "Dior Appoints Former Céline Designer as Accessories Creative Director",
        "excerpt": "The French house brings in fresh talent to oversee its leather goods division as it seeks to reinvigorate the Lady Dior and Saddle bag lines.",
        "source_name": "WWD",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.4,
    },

    # Gucci
    {
        "competitor": "Gucci",
        "event_type": "collection_launch",
        "title": "Gucci Cruise 2026 Collection Draws Inspiration from Japanese Gardens",
        "excerpt": "Sabato De Sarno's latest collection features delicate floral prints and kimono-inspired silhouettes, presented in a show at Kyoto's historic temples.",
        "source_name": "Vogue Business",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.3,
    },
    {
        "competitor": "Gucci",
        "event_type": "reputational_issue",
        "title": "Gucci Faces Criticism Over Cultural Appropriation in Latest Campaign",
        "excerpt": "The Italian brand has pulled advertising imagery after social media backlash over the use of sacred indigenous symbols without proper consultation or attribution.",
        "source_name": "Business of Fashion",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.7,
    },
    {
        "competitor": "Gucci",
        "event_type": "geographic_expansion",
        "title": "Gucci to Open Five New Stores Across Middle East in 2026",
        "excerpt": "Kering-owned brand accelerates expansion in Gulf region with boutiques planned for Dubai, Riyadh, and Doha as luxury spending surges.",
        "source_name": "Financial Times",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.7,
    },
    {
        "competitor": "Gucci",
        "event_type": "celebrity_or_influencer_alignment",
        "title": "Gucci Dresses Zendaya for Met Gala in Custom Archive Piece",
        "excerpt": "The actress wore a reimagined 1990s Tom Ford-era gown, sparking renewed interest in the brand's heritage collection among younger consumers.",
        "source_name": "WWD",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.5,
    },
    {
        "competitor": "Gucci",
        "event_type": "sustainability_or_sourcing",
        "title": "Gucci Launches Circular Resale Platform for Pre-Owned Handbags",
        "excerpt": "The Italian house enters the secondhand market with authentication services and buyback program, aiming to extend product lifecycles and reduce waste.",
        "source_name": "Business of Fashion",
        "source_type": "rss",
        "official_source": False,
        "impact": 4.0,
    },

    # Additional variety for trends
    {
        "competitor": "Chanel",
        "event_type": "collection_launch",
        "title": "Chanel Resort 2026 Presented in Cap d'Antibes",
        "excerpt": "The house showcases its cruise collection on the French Riviera, emphasizing vacation-ready pieces in lightweight fabrics.",
        "source_name": "Vogue",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.6,
    },
    {
        "competitor": "Dior",
        "event_type": "campaign_or_collaboration",
        "title": "Dior Partners with Anish Kapoor for Limited Edition Handbag Series",
        "excerpt": "The artist's signature mirror-finish aesthetic is applied to the Lady Dior bag in a limited run of 500 pieces.",
        "source_name": "WWD",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.8,
    },
    {
        "competitor": "Gucci",
        "event_type": "collection_launch",
        "title": "Gucci Fall 2026 RTW Features Bold Color Blocking",
        "excerpt": "De Sarno's sophomore ready-to-wear collection showcases vibrant palettes and oversized proportions.",
        "source_name": "Vogue Business",
        "source_type": "rss",
        "official_source": False,
        "impact": 3.9,
    },
]


def generate_url(title: str) -> str:
    """Generate a realistic-looking URL from title."""
    slug = title.lower().replace("'", "").replace(":", "")
    slug = "-".join(slug.split()[:8])
    return f"https://example.com/articles/{slug}-{random.randint(10000, 99999)}"


def generate_published_date(days_ago_range: tuple[int, int]) -> str:
    """Generate a realistic published date in ISO format."""
    days_ago = random.randint(*days_ago_range)
    hours_ago = random.randint(0, 23)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
    # Use simple format without microseconds for pandas compatibility
    return dt.replace(microsecond=0).isoformat()


def create_sample_data():
    """Generate and insert sample data into the database."""
    print("=" * 60)
    print("Sample Data Generator")
    print("=" * 60)

    init_db()

    inserted = 0
    for article in SAMPLE_ARTICLES:
        item_id = str(uuid.uuid4())

        # Create realistic URL
        source_url = generate_url(article["title"])

        # Distribute dates over last 30 days, with more recent articles
        if article.get("event_type") in ["collection_launch", "campaign_or_collaboration"]:
            # Recent launches
            published_at = generate_published_date((1, 10))
        else:
            # Spread across 30 days
            published_at = generate_published_date((1, 30))

        item = {
            "item_id": item_id,
            "competitor": article["competitor"],
            "source_type": article["source_type"],
            "source_name": article["source_name"],
            "source_url": source_url,
            "published_at": published_at,
            "title": article["title"],
            "excerpt": article["excerpt"],
            "raw_text": article["excerpt"],  # In real data this would be longer
            "translated_text": None,
            "original_language": "en",
            "official_source": article.get("official_source", False),
        }

        try:
            insert_item(item)
            inserted += 1
        except Exception as e:
            print(f"  Error inserting '{article['title'][:50]}...': {e}")

    print(f"\n✓ Inserted {inserted} sample articles")

    # Verify what we inserted
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    by_brand = conn.execute("""
        SELECT competitor, COUNT(*) as count
        FROM items
        GROUP BY competitor
    """).fetchall()
    conn.close()

    print(f"\nDatabase now contains {count} total items:")
    for row in by_brand:
        print(f"  • {row['competitor']}: {row['count']} articles")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("=" * 60)
    print("1. Run the pipeline to process data:")
    print("   python -m src.pipeline --skip-ingest")
    print()
    print("2. Launch the dashboard:")
    print("   streamlit run dashboard/app.py")
    print("=" * 60)


if __name__ == "__main__":
    create_sample_data()
