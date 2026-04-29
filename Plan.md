---
created: 2026-04-29
tags:
  - note
categories:
  - "[[Classes]]"
subject:
  - "[[AI for Business]]"
date: 2026-04-29
---
# Areas of Opportunity & AI/ML Ideas

## Part 1 — Areas of Opportunity

### A. Results / Output quality (highest leverage for an MBA grade)

1. **Sentiment is computed but never used.** `src/processing/sentiment.py` runs Twitter-RoBERTa on every item, but the score never reaches the brief, the trends formula, or the dashboard. This is the single biggest "free win": surface it, weight trend scores by it, show sentiment-flipped brands as alerts. — **DONE**
2. **Brief is a Jinja template with no synthesis.** `src/output/brief.py` `_build_implications` (lines 113–154) is generic rules ("brand X is silent", "brand Y dominates"). The brief lists items rather than telling a story. Even a small local LLM (or Claude API in a one-off) could turn the top events into 3 strategic paragraphs per brand. — **DONE** (via Ollama llama3.1:8b, see Part 2 #1)
3. **Event classification is ~80% keyword scoring**, only falling through to the zero-shot model when confidence < 0.35 (`extractor.py:157–196`). Flipping the default — zero-shot first, keywords as a cheap pre-filter — would raise classification quality and is defensible in the writeup. — **DONE**
4. **"Relevance score" = brand-mention count** (`extractor.py:112–120`). That's not relevance, that's frequency. A semantic similarity score against a per-brand reference embedding would be more honest and more accurate. — **DONE**
5. **Trend formula weights are hardcoded** (`trends.py:86–89`: 0.5/0.3/0.2). No ablation, no justification. For an MBA project, a one-page "we tried weights X/Y/Z and chose this because…" justifies the choice. — **DONE**

### B. Dashboard / presentation

6. **No time-series view.** Trends are shown as snapshots; the most compelling visual in competitive intelligence is "this brand's signal volume spiking over the last 14 days vs. competitors." You have the data — `items.published_at` + `events` — just not the chart. — **DONE**
7. **No sentiment visualization** (follows from A1). A diverging bar chart per brand (positive/negative share-of-voice) is one Plotly call away.
8. **No competitor comparison tab.** Side-by-side: Chanel vs Dior vs Gucci across event types over time. Currently each brand is shown in isolation.
9. **Brief is markdown only.** A "download PDF" button on the brief tab is a 10-line addition and looks great in a class demo.
10. **No "why this trend?" drill-down.** Clicking a trend should show the underlying articles and their embeddings/cluster. Streamlit `st.expander` per trend.

### C. Code quality (lower priority — works fine, but worth mentioning)

11. **O(n²) in semantic dedup** (`dedup.py`): fine at hundreds of items, breaks at thousands. Not urgent for the project but worth a one-line comment in the writeup acknowledging the scaling limit.
12. **Per-item DB query loop in clustering** (`clustering.py:75–88`) — could be one JOIN.
13. **Translation only handles Spanish** (`language.py:30–41`). If your sources include French/Italian luxury press (Vogue France, BoF Italia), you're silently dropping them.
14. **No structured logging.** `print()` everywhere makes pipeline debugging painful. `logging` module + a `--verbose` flag is 30 minutes of work.
15. **Zero-shot model loaded lazily inside the extraction loop** (`extractor.py:140`) — adds ~5s to the first event. Move to module init.

---

## Part 2 — Ideas to Lever AI/ML More

Pick 1–2 of these. Each is defensible as a "real ML contribution" in the writeup. Ranked by effort × academic impact.

### Tier 1 — High impact, moderate effort

1. (ALREADY DONE) **LLM-powered strategic synthesis in the brief.**

2. (ALREADY DONE)  **Fine-tune a small classifier on your event taxonomy.** 

3. **Anomaly detection for trends, not a hand-tuned formula.** Replace the weighted-sum trend score with `IsolationForest` or `LocalOutlierFactor` on (burst_z, source_count, sentiment_delta, impact). Frame it as "the model finds outliers; we don't have to guess weights." Ablation against the current formula is your evaluation.

### Tier 2 — Strong project-fit, lighter lift

4. (ALREADY DONE) **Semantic search over the corpus.** 

5. **Topic modeling beyond DBSCAN labels.** The current cluster "themes" are stopword-filtered top keywords (`clustering.py`). Replace with BERTopic or a c-TF-IDF over the cluster — produces real topic labels like *"sustainability sourcing controversy"* instead of *"chanel report water"*.

6. **Brand-similarity embeddings ("which competitor is doing what we're doing?").** Average each brand's article embeddings into a "brand vector" per week, plot the trajectory, show convergence/divergence between Chanel/Dior/Gucci. This is the kind of insight an MBA class loves.

### Tier 3 — Stretch

7. **Multilingual upgrade.** Swap `all-MiniLM-L6-v2` → `paraphrase-multilingual-MiniLM-L12-v2` and you can drop the translation step entirely. Embeddings stay aligned cross-language. Stale-embedding detection is already in place (`get_items_with_stale_embeddings`), so the migration is clean.

8. **RAG-based "ask the corpus".** Put the embeddings in a small FAISS/Chroma index, expose a Streamlit chat tab that answers free-form questions ("what's Dior's sustainability narrative this month?") by retrieving top-k items and feeding them to an LLM. Big demo moment.

9. **Forecasting next week's spike per brand.** Simple Prophet or even a 7-day rolling regression on event counts per brand × event_type. "We predicted Gucci would spike on collection_launch this week, and they did" is a great slide.
