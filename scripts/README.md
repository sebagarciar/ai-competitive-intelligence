# Scripts

Utility scripts for the AI Competitive Intelligence Copilot.

## Available Scripts

### `generate_sample_data.py`
Creates realistic sample data for testing and demos without waiting for real ingestion.

**Usage:**
```bash
python scripts/generate_sample_data.py
```

**What it does:**
- Inserts 16 realistic articles across Chanel, Dior, and Gucci
- Covers all 8 event types in the taxonomy
- Distributes articles over the past 30 days
- Creates variety for trend detection

**After running, process the data:**
```bash
python -m src.pipeline --skip-ingest
```

### `check_status.py`
Shows the current state of the database and system health.

**Usage:**
```bash
python scripts/check_status.py
```

**What it shows:**
- Database item counts (articles, embeddings, events, trends)
- Coverage by brand
- Top event types
- Latest trends detected
- Most recent brief generated

## Quick Start Workflow

```bash
# 1. Generate sample data
python scripts/generate_sample_data.py

# 2. Process it through the pipeline
python -m src.pipeline --skip-ingest

# 3. Check status
python scripts/check_status.py

# 4. Launch dashboard
streamlit run dashboard/app.py
```

This workflow lets you see the entire system working in under 2 minutes.
