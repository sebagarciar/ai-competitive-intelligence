AI Competitive Intelligence Copilot for Luxury Fashion
1. Objective

Build a working AI prototype that monitors a small set of luxury fashion brands and transforms fragmented public information into structured competitive intelligence and weekly strategic briefs.

The system focuses on brand positioning signals, not just hard business events.

2. Business Problem

Luxury brands like Chanel operate in an environment where:

Strategic signals are distributed across fashion media, news, and brand-owned content
Information is qualitative, narrative-driven, and fragmented
Analysts must manually interpret weak signals (campaigns, themes, positioning shifts)
Important developments are easily missed or misinterpreted

Goal:
Automate the collection, structuring, and interpretation of these signals to support strategy, marketing, and brand teams.

3. Scope (MVP)
Brands
Chanel (primary focus)
2–3 competitors (recommended: Dior, Gucci)
Languages
English (EN)
Spanish (ES)
Time Window
30-day rolling window
4. Data Sources
4.1 Primary Sources (High Priority)
Fashion & Luxury Media
Vogue Business
Business of Fashion (BoF)
WWD (Women’s Wear Daily)
Financial Times (luxury/fashion section)
News Aggregation
GDELT DOC 2.0 API (multilingual, near real-time)
Brand-Owned Content
Chanel official website (news, collections)
Competitor official sites
4.2 Secondary Sources (Optional)
NewsAPI (development use only)
Google News (manual validation)
4.3 Excluded from MVP
X (Twitter) API (cost/instability)
LinkedIn API (restricted access)
Instagram scraping (not reliable at scale)
5. System Architecture
5.1 Tech Stack
Python
SQLite or PostgreSQL
Pandas
requests / feedparser / BeautifulSoup / trafilatura
Embeddings (OpenAI or sentence-transformers)
LLM API (for structured extraction)
Streamlit (demo UI)
5.2 Pipeline Overview
Ingestion
Pull articles from sources
Store raw data
Normalization
Clean text
Standardize fields
Language Processing
Detect language (EN / ES)
Translate Spanish → English
Store both original and translated text
Deduplication
Remove identical URLs
Merge semantically similar articles
Event Extraction (LLM)
Convert unstructured text → structured JSON
Embedding + Clustering
Group similar items into themes
Trend Detection
Identify emerging patterns
Output Generation
Structured event database
Weekly intelligence brief
6. Data Schema
6.1 Normalized Item
item_id
competitor
source_type
source_name
source_url
published_at
title
excerpt
raw_text
translated_text
original_language
official_source (bool)
6.2 Event Record
item_id
competitor
event_type
business_function
relevance_score (1–5)
impact_score (1–5)
summary
evidence_snippet
confidence_score
duplicate_group_id
7. Event Taxonomy (Luxury-Focused)
collection_launch
campaign_or_collaboration
pricing_or_exclusivity
geographic_expansion
creative_direction
sustainability_or_sourcing
celebrity_or_influencer_alignment
reputational_issue
8. Trend Detection Method
8.1 Approach

Hybrid method combining:

classification (event types)
semantic clustering (themes)
statistical burst detection
8.2 Metrics

For each:

competitor + event_type + cluster

Compute:

count_7d
mean_prev_28d
std_prev_28d
unique_sources
avg_impact
8.3 Formula
burst_z = (count_7d - mean_prev_28d) / (std_prev_28d + 1)

trend_score = 
  0.5 * burst_z +
  0.3 * log(1 + unique_sources) +
  0.2 * (avg_impact / 5)
8.4 Trend Rules

Flag as trend if:

trend_score ≥ threshold
AND:
unique_sources ≥ 2
OR official_source = true AND impact_score ≥ 4
8.5 Two Output Lanes
Critical Events
Single high-impact events (e.g., major campaign, controversy)
Emerging Trends
Repeated or clustered signals over time
9. Multilingual Processing
Design
Ingest EN + ES content
Translate ES → EN for analysis
Store both versions
Processing Standard

All downstream tasks run in English:

classification
clustering
trend detection
10. Outputs
10.1 Structured Event Feed

Queryable database with filters:

competitor
event type
date
10.2 Weekly Intelligence Brief

Sections:

Executive Summary
Top Competitor Moves
Emerging Trends
Critical Events
Strategic Implications
Source Links
10.3 Dashboard (Streamlit)
Event table
Filters
Trend visualization
Generated report view
11. Evaluation Metrics
11.1 Relevance Precision@10

Top 10 items → % useful

11.2 Event Classification (F1 Score)

Compare model vs human-labeled dataset

11.3 Trend Precision@5

Top 5 trends → % judged valid by humans

11.4 Optional: Time Saved

Manual vs automated report creation time

12. Constraints
No login-protected scraping
No unstable APIs (X, LinkedIn)
No autonomous browsing agents
Focus on reliability over complexity
13. Implementation Priorities
Reliable ingestion
Clean structured extraction
Basic deduplication
Working trend detection
Clear output (brief + dashboard)
14. Deliverables
Source connectors
Processing pipeline
Database schema
Trend detection module
Streamlit dashboard
Evaluation notebook
README with setup instructions
15. Key Value Proposition

Transforms fragmented fashion and business coverage into:

structured insights
detectable strategic patterns
actionable weekly intelligence

Reduces manual analysis time and improves strategic awareness.