"""
Centralized query generation for social media ingestion adapters.
Generates multiple search query variants per brand to improve coverage.
"""

BRANDS = ["Chanel", "Dior", "Gucci"]
COMPETITORS = {brand: [b for b in BRANDS if b != brand] for brand in BRANDS}


def build_queries(brand: str, mode: str = "full") -> list[str]:
    """
    Build search queries for a brand.

    mode='full'   → multiple variants covering reviews, pricing, comparisons, etc.
    mode='simple' → just the brand name (used as retry fallback when full queries return thin results)
    """
    if mode == "simple":
        return [brand]

    comps = COMPETITORS.get(brand, [])
    queries = [
        brand,
        f"{brand} review",
        f"{brand} pricing",
        f"{brand} collection",
        f"{brand} quality",
        f"{brand} alternatives",
    ]
    for comp in comps:
        queries.append(f"{brand} vs {comp}")

    return queries
