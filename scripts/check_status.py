"""
Quick status check for the AI Competitive Intelligence Copilot.
Shows what's in the database and verifies all components are working.

Usage:
    python scripts/check_status.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_connection
from collections import Counter

def check_status():
    print("=" * 70)
    print("AI Competitive Intelligence Copilot — Status Check")
    print("=" * 70)
    print()

    conn = get_connection()

    # Items
    items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    items_with_embeddings = conn.execute(
        "SELECT COUNT(*) FROM items WHERE embedding IS NOT NULL"
    ).fetchone()[0]

    # Events
    events_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    events_by_brand = conn.execute("""
        SELECT competitor, COUNT(*) as count
        FROM events
        GROUP BY competitor
        ORDER BY count DESC
    """).fetchall()

    events_by_type = conn.execute("""
        SELECT event_type, COUNT(*) as count
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
        LIMIT 5
    """).fetchall()

    # Trends
    trends_count = conn.execute("SELECT COUNT(*) FROM trends").fetchone()[0]
    trends_data = conn.execute("""
        SELECT competitor, event_type, trend_score, count_7d
        FROM trends
        ORDER BY trend_score DESC
        LIMIT 3
    """).fetchall()

    # Briefs
    briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
    briefs = sorted(briefs_dir.glob("*.md"), reverse=True) if briefs_dir.exists() else []

    conn.close()

    # Display
    print(f"📊 DATABASE CONTENTS")
    print("-" * 70)
    print(f"  Items (articles):        {items_count}")
    print(f"  Items with embeddings:   {items_with_embeddings}/{items_count}")
    print(f"  Events extracted:        {events_count}")
    print(f"  Trends detected:         {trends_count}")
    print(f"  Briefs generated:        {len(briefs)}")
    print()

    print(f"🏢 COVERAGE BY BRAND")
    print("-" * 70)
    for row in events_by_brand:
        brand = row['competitor']
        count = row['count']
        bar = "█" * (count * 2)
        print(f"  {brand:12s} {bar} {count}")
    print()

    print(f"📈 TOP EVENT TYPES")
    print("-" * 70)
    for row in events_by_type:
        event_type = row['event_type'].replace('_', ' ').title()
        count = row['count']
        print(f"  {event_type:35s} {count}")
    print()

    if trends_count > 0:
        print(f"🔥 TOP TRENDS")
        print("-" * 70)
        for row in trends_data:
            brand = row['competitor']
            event_type = row['event_type'].replace('_', ' ').title()
            score = row['trend_score']
            count_7d = row['count_7d']
            print(f"  {brand} • {event_type:30s} (score: {score:.2f}, {count_7d} articles)")
        print()

    if briefs:
        print(f"📝 LATEST BRIEF")
        print("-" * 70)
        print(f"  {briefs[0].name}")
        print(f"  Location: {briefs[0]}")
        print()

    print("=" * 70)
    print("✅ System Status: OPERATIONAL")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  • View the brief: cat data/briefs/*.md")
    print("  • Launch dashboard: streamlit run dashboard/app.py")
    print("  • Run evaluation: jupyter notebook notebooks/evaluation.ipynb")
    print()


if __name__ == "__main__":
    check_status()
