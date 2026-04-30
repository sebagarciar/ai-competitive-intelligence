# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Competitive Intelligence Copilot for luxury fashion brands (Chanel, Dior, Gucci). The system ingests articles from public sources, processes them without paid LLM APIs using local models, and generates strategic intelligence briefs. Architecture follows a pipeline pattern: ingest → process → analyze → output.

## Common Commands

```bash
# Run full pipeline (ingest, process, analyze, generate brief)
python -m src.pipeline

# Skip ingestion (use existing data)
python -m src.pipeline --skip-ingest

# Skip local LLM synthesis (use deterministic rule-based implications instead)
python -m src.pipeline --no-llm

# Skip zero-shot classification (keyword-only extraction, faster but lower quality)
python -m src.pipeline --no-zero-shot

# Launch Streamlit dashboard (8 tabs: digest, trends, perception, compare, brief, sources, event feed, search)
streamlit run dashboard/app.py

# Initialize database manually
python -m src.db

# Run evaluation notebook
jupyter notebook notebooks/evaluation.ipynb
```

## Architecture

### Pipeline Flow (`src/pipeline.py`)
The pipeline orchestrates seven sequential stages:

1. **Ingest** (`ingest()`) — Fetches articles from GDELT, RSS feeds, and brand sites. Deduplicates by URL before insertion.
2. **Normalize** (`normalize_item()`) — Cleans HTML, standardizes dates via `src/processing/normalizer.py`.
3. **Language** (`process_language()`) — Detects language with `langdetect`, translates Spanish→English using Google Translate free tier.
4. **Embed** (`embed()`) — Generates 384-dim embeddings via local `all-MiniLM-L6-v2` model. Stored as BLOBs in SQLite.
5. **Deduplicate** — Semantic deduplication using cosine similarity (threshold: 0.92).
6. **Extract** (`extract()`) — Event classification: keywords act as a fast pre-filter (skip zero-shot when `kw_conf >= KEYWORD_CONFIDENCE_THRESHOLD=0.35`); zero-shot (`cross-encoder/nli-MiniLM2-L6-H768`) is the primary classifier for ambiguous items. Zero-shot is enabled by default (`use_zero_shot=True`); disable with `--no-zero-shot` for faster runs.
7. **Cluster** (`run_clustering()`) — DBSCAN on embeddings to discover semantic themes.
8. **Trends** (`detect_trends()`) — Burst detection formula: `trend_score = 0.45*burst_z + 0.27*log(1+sources) + 0.18*(impact/5) + 0.10*avg_sentiment`. Flags Critical Events (single high-impact article from official source). `avg_sentiment` is persisted in the trends table.
9. **Brief** (`generate_brief()`) — Jinja2 template rendering. Saves to `data/briefs/brief_YYYYMMDD.md`.

### Database Schema (`src/db.py`)
SQLite with WAL mode (`intelligence.db`):
- **items** — Raw articles with embeddings (BLOB), translations, metadata
- **events** — Classified events linked to items (event_type, impact_score, relevance_score, cluster_id)
- **trends** — Detected trends with burst statistics (trend_score, is_critical flag, avg_sentiment)

Critical: The DB uses foreign keys (`PRAGMA foreign_keys=ON`). Events reference items via `item_id`.

### Event Taxonomy
8 categories: `collection_launch`, `campaign_or_collaboration`, `pricing_or_exclusivity`, `geographic_expansion`, `creative_direction`, `sustainability_or_sourcing`, `celebrity_or_influencer_alignment`, `reputational_issue`.

### Data Sources
- **GDELT DOC 2.0** — Free news aggregator, 30-day rolling window, no API key
- **RSS feeds** — Vogue Business, BoF, WWD, Financial Times (brand-filtered)
- **Brand sites** — Official news pages (flagged with `official_source = True`)
- **YouTube** — Official channels + keyword search (`YOUTUBE_API_KEY`)
- **Webhose.io** — News API with social share metrics (`WEBHOSE_API_KEY`)
- **Reddit** — PRAW subreddit browsing + keyword search via `reddit.subreddit("all").search()` (`REDDIT_CLIENT_ID/SECRET`)
- **Bluesky** — AT Protocol search API; requires `BSKY_IDENTIFIER` and `BSKY_APP_PASSWORD` (`src/ingestion/bluesky.py`)
- **X via Grok** — xAI Grok live X search; requires `XAI_API_KEY`; gracefully skipped if absent (`src/ingestion/grok_search.py`)

### Social Listening Architecture
Social adapters (Reddit, Bluesky, Grok) share a **query planner** (`src/ingestion/query_planner.py`):
- `build_queries(brand, mode="full")` → list of search variants: `"{brand}"`, `"{brand} review"`, `"{brand} pricing"`, `"{brand} collection"`, `"{brand} vs {competitor}"` (×2), `"{brand} quality"`, `"{brand} alternatives"`
- `mode="simple"` → returns just `[brand]`, used by the pipeline retry path
- The pipeline wraps social adapters in `_fetch_simple()`: if a source returns < 3 results, it retries with `simple=True`
- All adapters accept `fetch_all(simple: bool = False)` and return items in the standard schema

### Dashboard (`dashboard/app.py`)
Streamlit app with 8 tabs:
1. **Digest** — Top stories and critical event highlights
2. **Trends** — Bar/scatter charts + 14-day signal volume time-series per brand
3. **Perception** — Sentiment charts: avg per brand, distribution pie, diverging share-of-voice bar (positive/negative % per brand), positive/negative article lists
4. **Compare** — Side-by-side competitor comparison: per-brand KPI cards, grouped and normalised event-mix bars, daily activity time-series with event-type filter, impact × relevance scatter
5. **Weekly Brief** — Markdown render of latest brief + "Download PDF" button (generates styled A4 PDF via `fpdf2`)
6. **Source Coverage** — Pie/bar charts for source attribution
7. **Event Feed** — Filterable full event table with sentiment badges
8. **Search** — Semantic search over the full corpus (cosine similarity on stored embeddings, top-10 results)

The dashboard caches data queries with TTL=300s. "Run Pipeline Now" button triggers full pipeline and clears cache.

## Development Notes

- **No paid LLM APIs**: All ML uses local models (sentence-transformers, transformers). Translation uses free Google Translate tier. Optional paid sources (Webhose, xAI) are gracefully skipped when keys are absent.
- **Embedding model**: `all-MiniLM-L6-v2` loaded lazily on first use via global singleton in `src/processing/embeddings.py`. Model name is stored alongside each embedding BLOB (`embedding_model` column); use `get_items_with_stale_embeddings(current_model)` to detect rows that need re-embedding after a model swap.
- **Deduplication**: URL exact-match happens during ingestion; semantic dedup at 0.92 cosine threshold happens post-embedding.
- **Tuning constants**: All ML/analysis thresholds live in `src/config.py` and can be overridden via environment variables (e.g. `DBSCAN_EPS=0.3 python -m src.pipeline`). Current defaults: `TREND_SCORE_THRESHOLD=0.3`, `MIN_UNIQUE_SOURCES=1`, `CRITICAL_IMPACT_THRESHOLD=3.5`, `SEMANTIC_SIMILARITY_THRESHOLD=0.92`, `DBSCAN_EPS=0.25`. Trend formula weights: `TREND_WEIGHT_BURST=0.45`, `TREND_WEIGHT_SOURCES=0.27`, `TREND_WEIGHT_IMPACT=0.18`, `TREND_WEIGHT_SENTIMENT=0.10`.
- **Pipeline can run incrementally**: Use `--skip-ingest` to reprocess existing data. Each stage checks for missing data (e.g., `get_items_without_embeddings()`) to avoid redundant work.
- **Brand colors** (used in dashboard): Chanel `#1a1a1a`, Dior `#b5936c`, Gucci `#5a7a4e`.
- **Grok/xAI HTTP client**: `grok_search.py` uses `httpx` (not `requests`) for the xAI API call. If `httpx` is not installed, the adapter skips gracefully with a warning.
- **Local LLM brief synthesis**: The "Strategic Implications" section of the weekly brief is generated by a local Llama 3.1 8B Instruct model served via Ollama (`src/output/llm_synthesis.py`). Setup: `brew install ollama && ollama pull llama3.1:8b && ollama serve`. Results are cached per `(brand, prompt_hash)` in the `brief_synthesis_cache` table. If Ollama is unreachable or `--no-llm` is passed, the brief falls back to the deterministic `_build_implications` rules. Tunable via `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TEMPERATURE` (default 0.3), `OLLAMA_SEED`, `LLM_SYNTHESIS_ENABLED`.
- **PDF generation** (`dashboard/app.py::_brief_to_pdf`): Uses `fpdf2` (must be installed: `pip install fpdf2`). In fpdf2 ≥2.7 `multi_cell` defaults to `new_x=XPos.RIGHT`, leaving the cursor at the right edge after each call — always call `pdf.set_x(pdf.l_margin)` afterwards. Helvetica does not support Unicode; non-latin-1 characters (emoji, CJK, em-dash) must be sanitised before passing to `multi_cell`.
- **Dashboard PLOTLY_DARK**: The `PLOTLY_DARK` dict includes a `title` key. Never pass `title=` as an explicit kwarg in the same `update_layout(**PLOTLY_DARK, title=...)` call — it causes a `TypeError: multiple values for keyword argument`. Always do two separate `update_layout` calls: one with `**PLOTLY_DARK`, one with `title=dict(...)`.

## Evaluation Metrics
Metric functions live in `src/evaluation.py` (importable, testable):
- `precision_at_k(labels, k=10)` — fraction of top-k items judged relevant
- `event_f1(y_true, y_pred)` — returns `{macro, weighted, report}` dict using sklearn
- `trend_precision_at_k(labels, k=5)` — fraction of top-k trends judged valid
- `run_trend_ablation(events, weight_configs)` — evaluates multiple trend formula weight sets using three unsupervised proxy metrics (spearman_corr, high_impact_mean_rank, top5_mean_impact); used to justify the chosen weights without hand-labeled trends

`notebooks/evaluation.ipynb` imports from `src.evaluation` and provides the manual labeling workflow. The notebook also contains:
- **Classifier fine-tuning**: label ~150 events, train a `LogisticRegression` on the stored 384-dim embeddings, compare F1 vs keyword baseline, save to `data/event_classifier.joblib`. Set `USE_TRAINED_CLASSIFIER=1` to activate in the pipeline.
- **Trend weight ablation**: 5 candidate weight configurations compared across proxy metrics; chart saved to `data/trend_weight_ablation.png`. Rationale for chosen weights (burst=0.45, sources=0.27, impact=0.18, sentiment=0.10) documented inline.

## Relevance Scoring
`relevance_score` in the events table is computed as **cosine similarity** between the article's stored 384-dim embedding and a per-brand reference embedding (`BRAND_REFERENCES` in `src/processing/extractor.py`), mapped to [1.0, 5.0]. Falls back to brand-mention count if no embedding is available. Reference embeddings are pre-warmed before the extraction loop and cached in-process.
