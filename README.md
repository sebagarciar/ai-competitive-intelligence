# AI Competitive Intelligence Copilot — Luxury Fashion

Monitors Chanel, Dior, and Gucci across public sources and produces structured competitive intelligence + weekly strategic briefs. Runs entirely **without a paid LLM API**.

## Quick Start

```bash
# 1. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 2. Run the full pipeline (ingest → process → analyze → brief)
python -m src.pipeline

# 3. Launch the Streamlit dashboard
streamlit run dashboard/app.py
```

## Demo with Sample Data

Want to see the system working immediately? Generate sample data instead of waiting for real ingestion:

```bash
# 1. Generate 16 realistic sample articles
python scripts/generate_sample_data.py

# 2. Process through the pipeline (embeddings, events, trends, brief)
python -m src.pipeline --skip-ingest

# 3. Check system status
python scripts/check_status.py

# 4. Launch dashboard to explore
streamlit run dashboard/app.py
```

This workflow demonstrates the full system in under 2 minutes.

## Project Structure

```
├── src/
│   ├── db.py                    # SQLite schema + CRUD
│   ├── pipeline.py              # End-to-end orchestrator
│   ├── ingestion/
│   │   ├── gdelt.py             # GDELT DOC 2.0 API
│   │   ├── rss_feeds.py         # Vogue Business, BoF, WWD, FT
│   │   └── brand_sites.py       # Official brand news pages
│   ├── processing/
│   │   ├── normalizer.py        # Text cleaning
│   │   ├── language.py          # Language detect + ES→EN translation
│   │   ├── embeddings.py        # sentence-transformers (local)
│   │   ├── dedup.py             # URL + semantic deduplication
│   │   └── extractor.py         # Event classification (keyword + zero-shot)
│   ├── analysis/
│   │   ├── clustering.py        # DBSCAN theme clustering
│   │   └── trends.py            # Burst detection + trend scoring
│   └── output/
│       └── brief.py             # Jinja2 weekly intelligence brief
├── dashboard/
│   └── app.py                   # Streamlit dashboard (4 tabs)
├── notebooks/
│   └── evaluation.ipynb         # Precision@10, F1, Trend Precision@5
├── data/
│   ├── intelligence.db          # SQLite database (auto-created)
│   └── briefs/                  # Generated markdown briefs
└── requirements.txt
```

## Data Sources

| Source | Type | Notes |
|---|---|---|
| GDELT DOC 2.0 | News aggregator | Free API, no key needed, 30-day window |
| Vogue Business RSS | Fashion media | Brand-filtered |
| Business of Fashion RSS | Fashion media | Brand-filtered |
| WWD RSS | Fashion media | Brand-filtered |
| Financial Times RSS | Financial media | Luxury section |
| Chanel / Dior / Gucci official sites | Brand-owned | `official_source = True` |

## Pipeline Steps

1. **Ingest** — pull articles from all sources, skip known URLs
2. **Normalize** — clean HTML, standardize dates
3. **Language** — detect language, translate ES→EN via Google Translate (free tier)
4. **Embed** — compute sentence embeddings with `all-MiniLM-L6-v2` (local model)
5. **Deduplicate** — URL exact-match + cosine similarity threshold (0.92)
6. **Extract** — classify event type using keyword scoring; optional zero-shot fallback
7. **Cluster** — DBSCAN on embeddings to discover semantic themes
8. **Trends** — burst detection formula; flag Critical Events and Emerging Trends
9. **Brief** — generate markdown weekly intelligence report via Jinja2 templates

## Event Taxonomy

`collection_launch` · `campaign_or_collaboration` · `pricing_or_exclusivity` · `geographic_expansion` · `creative_direction` · `sustainability_or_sourcing` · `celebrity_or_influencer_alignment` · `reputational_issue`

## Evaluation

Open `notebooks/evaluation.ipynb` and follow the instructions to:
- Label top 10 items → **Relevance Precision@10**
- Label 20 event classifications → **Event F1 Score**
- Label top 5 trends → **Trend Precision@5**
