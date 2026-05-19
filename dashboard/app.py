"""
Streamlit dashboard for AI Competitive Intelligence Copilot.

Editorial-intelligence redesign — Bloomberg Terminal × Vogue Business.
All data logic preserved verbatim from the original; only layout, styling,
and component choices have changed.

Run with:
    streamlit run dashboard/app.py
"""
import json as _json
import re as _re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import re
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mistune
from datetime import datetime, timezone
from src.db import init_db, get_connection, get_latest_trends, get_all_items_with_embeddings
from src.output.brief import generate_brief
from src.processing.embeddings import embed_text, from_bytes

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Chanel — Competitive Intelligence",
    page_icon="🖤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Editorial CSS — Bloomberg × Vogue Business
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ---------- Typography ---------- */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, .stMarkdown p,
[data-testid="stSidebar"], [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
}

.stApp {
    background: #fafaf7;
}

/* Hide the default Streamlit chrome we don't want */
#MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; height: 0; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; max-width: 1500px; }

/* ---------- Sidebar collapse toggle ---------- */
[data-testid="stSidebarCollapsedControl"] {
    background: rgba(80, 80, 80, 0.35) !important;
    border-radius: 0 4px 4px 0 !important;
    backdrop-filter: blur(4px);
}
[data-testid="stSidebarCollapsedControl"]:hover {
    background: rgba(201, 169, 110, 0.45) !important;
}
[data-testid="stSidebarCollapsedControl"] svg {
    color: #e8e6df !important;
    fill: #e8e6df !important;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: #1a1a1a !important;
    border-right: 1px solid #2a2a2a;
}
[data-testid="stSidebar"] * {
    color: #e8e6df !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] label {
    color: #c9a96e !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #242424 !important;
    border: 1px solid #333 !important;
    border-radius: 2px !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #c9a96e !important;
    color: #1a1a1a !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span {
    color: #1a1a1a !important;
}
[data-testid="stSidebar"] hr {
    border-color: #2a2a2a !important;
    margin: 1.2rem 0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
    background: #c9a96e !important;
    color: #1a1a1a !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.7rem 1rem !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    transition: background 0.15s ease;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #d9bc81 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #c9a96e !important;
    border: 1px solid #c9a96e !important;
}

/* Sidebar logo block */
.cc-logo {
    padding: 0.4rem 0 1.4rem;
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 1.2rem;
}
.cc-logo .mark {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.1rem;
    font-weight: 500;
    color: #ffffff;
    letter-spacing: 0.32em;
    line-height: 1;
    margin-bottom: 0.35rem;
}
.cc-logo .mark .amp {
    color: #c9a96e;
    font-style: italic;
    margin: 0 0.04em;
}
.cc-logo .tag {
    font-size: 0.62rem;
    color: #888;
    letter-spacing: 0.28em;
    text-transform: uppercase;
}

/* Sidebar status chip */
.cc-status {
    background: #242424;
    border-left: 2px solid #c9a96e;
    padding: 0.7rem 0.9rem;
    margin-bottom: 1rem;
}
.cc-status .label {
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 0.25rem;
}
.cc-status .value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #e8e6df;
}
.cc-status .pulse {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #5a8a5a;
    margin-right: 6px;
    box-shadow: 0 0 0 0 rgba(90, 138, 90, 0.7);
    animation: pulse 2s infinite;
    vertical-align: middle;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(90, 138, 90, 0.6); }
    70% { box-shadow: 0 0 0 6px rgba(90, 138, 90, 0); }
    100% { box-shadow: 0 0 0 0 rgba(90, 138, 90, 0); }
}

/* ---------- Masthead ---------- */
.cc-masthead {
    border-top: 3px solid #1a1a1a;
    border-bottom: 1px solid #1a1a1a;
    padding: 1.5rem 0 1.1rem;
    margin: 0 0 1.4rem;
    background: #fafaf7;
}
.cc-masthead .topline {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 0.6rem;
    border-bottom: 1px solid #e6e3da;
    padding-bottom: 0.5rem;
}
.cc-masthead .topline .right { color: #c9a96e; }
.cc-masthead h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 3.2rem !important;
    font-weight: 400 !important;
    line-height: 1 !important;
    letter-spacing: -0.01em !important;
    color: #1a1a1a !important;
    margin: 0 0 0.35rem 0 !important;
}
.cc-masthead h1 em {
    font-style: italic;
    color: #c9a96e;
    font-weight: 300;
}
.cc-masthead .dek {
    font-size: 0.82rem;
    color: #555;
    letter-spacing: 0.05em;
    max-width: 60ch;
}

/* ---------- Section headers (editorial) ---------- */
.cc-section-eyebrow {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin: 0.8rem 0 0.6rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #c9a96e;
}
.cc-section-eyebrow::before {
    content: "";
    display: inline-block;
    width: 22px; height: 1px;
    background: #c9a96e;
}
.cc-section-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.85rem;
    font-weight: 500;
    color: #1a1a1a;
    margin: 0 0 0.2rem;
    letter-spacing: -0.005em;
    line-height: 1.1;
}
.cc-section-dek {
    font-size: 0.85rem;
    color: #6b6b6b;
    margin-bottom: 1.1rem;
    border-bottom: 1px solid #e6e3da;
    padding-bottom: 0.85rem;
}

/* ---------- KPI strip (terminal-style) ---------- */
.cc-kpi-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0;
    border: 1px solid #1a1a1a;
    background: #1a1a1a;
    margin-bottom: 1.2rem;
}
.cc-kpi {
    background: #fafaf7;
    padding: 0.85rem 1rem;
    border-right: 1px solid #1a1a1a;
}
.cc-kpi:last-child { border-right: none; }
.cc-kpi .label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 0.3rem;
}
.cc-kpi .value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.95rem;
    font-weight: 500;
    color: #1a1a1a;
    line-height: 1;
}
.cc-kpi .delta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #c9a96e;
    margin-top: 0.2rem;
}
.cc-kpi.gold .value { color: #c9a96e; }
.cc-kpi.alert .value { color: #b8463f; }

/* ---------- Tabs (editorial nav) ---------- */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #1a1a1a !important;
    gap: 0 !important;
    background: transparent !important;
    margin-bottom: 1.2rem !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    padding: 0.7rem 1.2rem !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: #6b6b6b !important;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #1a1a1a !important; }
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #1a1a1a !important;
    border-bottom: 2px solid #c9a96e !important;
    font-weight: 600 !important;
}

/* ---------- News-feed cards (Event/Move) ---------- */
.cc-feed { margin-top: 0.4rem; }
.cc-feed-item {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: 1.4rem;
    padding: 1.2rem 0;
    border-bottom: 1px solid #e6e3da;
}
.cc-feed-item:last-child { border-bottom: none; }
.cc-feed-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #888;
}
.cc-feed-meta .date { color: #1a1a1a; font-weight: 600; }
.cc-feed-meta .impact-bar {
    margin-top: 0.5rem;
    display: flex;
    gap: 2px;
}
.cc-feed-meta .impact-bar span {
    flex: 1;
    height: 3px;
    background: #e6e3da;
}
.cc-feed-meta .impact-bar span.on { background: #c9a96e; }
.cc-feed-body .brand {
    display: inline-block;
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    font-size: 0.95rem;
    color: #c9a96e;
    margin-right: 0.6rem;
    letter-spacing: 0.05em;
}
.cc-feed-body .etype {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #888;
    border-left: 1px solid #d4d0c4;
    padding-left: 0.6rem;
}
.cc-feed-body h3 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 1.25rem !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
    line-height: 1.25 !important;
    margin: 0.3rem 0 0.45rem !important;
}
.cc-feed-body h3 a {
    color: #1a1a1a !important;
    text-decoration: none !important;
    border-bottom: 1px solid transparent !important;
    transition: border-color 0.15s;
}
.cc-feed-body h3 a:hover { border-bottom-color: #c9a96e !important; }
.cc-feed-body .summary {
    font-size: 0.88rem;
    color: #444;
    line-height: 1.55;
    margin-bottom: 0.6rem;
    max-width: 75ch;
}
.cc-feed-body .source-line {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #888;
}
.cc-feed-body .source-line .official {
    color: #c9a96e;
    border: 1px solid #c9a96e;
    padding: 1px 5px;
    margin-left: 6px;
    font-size: 0.58rem;
    letter-spacing: 0.16em;
}

/* Critical event card — masthead-style alert */
.cc-critical {
    border-top: 2px solid #b8463f;
    border-bottom: 1px solid #e6e3da;
    background: #fff;
    padding: 0.95rem 1.1rem;
    margin-bottom: 0.5rem;
}
.cc-critical-body { width: 100%; }
.cc-critical .label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #b8463f;
    font-weight: 600;
    margin-bottom: 0.25rem;
}
.cc-critical .headline {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: #1a1a1a;
}
.cc-critical .headline .brand {
    font-style: italic;
    color: #c9a96e;
    margin-right: 0.5rem;
}
.cc-critical-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.95rem;
    color: #333;
    margin: 0.3rem 0 0.4rem 0;
}
.cc-critical-title a { color: #333; text-decoration: underline; }
.cc-critical-snippet {
    font-size: 0.82rem;
    color: #555;
    line-height: 1.5;
    margin-bottom: 0.5rem;
    font-style: italic;
}
.cc-critical-footer {
    display: flex;
    justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: #888;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Trend card */
.cc-trend {
    padding: 0.85rem 0;
    border-bottom: 1px solid #e6e3da;
}
.cc-trend:last-child { border-bottom: none; }
.cc-trend .row1 {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.35rem;
}
.cc-trend .label {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.05rem;
    color: #1a1a1a;
}
.cc-trend .label .brand {
    font-style: italic;
    color: #c9a96e;
}
.cc-trend .score {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #1a1a1a;
    font-weight: 600;
}
.cc-trend .bar {
    height: 2px;
    background: #e6e3da;
    margin-bottom: 0.35rem;
}
.cc-trend .bar > div {
    height: 2px;
    background: #c9a96e;
}
.cc-trend .meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #888;
}

/* ---------- Brief (PDF-style) ---------- */
.cc-brief-doc {
    background: #ffffff;
    border: 1px solid #e6e3da;
    box-shadow: 0 1px 0 rgba(0,0,0,0.02), 0 12px 30px -18px rgba(26,26,26,0.18);
    padding: 3.5rem 4.5rem;
    margin: 0.5rem 0 1.5rem;
    max-width: 880px;
    margin-left: auto;
    margin-right: auto;
}
.cc-brief-doc .docline {
    border-top: 2px solid #1a1a1a;
    border-bottom: 1px solid #1a1a1a;
    padding: 0.8rem 0;
    display: flex;
    justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 2.5rem;
}
.cc-brief-doc .docline .right { color: #c9a96e; }
.cc-brief-doc h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 2.6rem !important;
    font-weight: 400 !important;
    color: #1a1a1a !important;
    margin: 0 0 0.4rem !important;
    line-height: 1.05 !important;
}
.cc-brief-doc h2 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 1.6rem !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
    margin: 2.2rem 0 0.8rem !important;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #e6e3da;
}
.cc-brief-doc h3 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 1.2rem !important;
    font-style: italic !important;
    color: #c9a96e !important;
    margin: 1.4rem 0 0.6rem !important;
    font-weight: 500 !important;
}
.cc-brief-doc p, .cc-brief-doc li {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.7 !important;
    color: #2a2a2a !important;
}
.cc-brief-doc em {
    color: #6b6b6b;
    font-size: 0.82rem;
}
.cc-brief-doc hr { border: none; border-top: 1px solid #e6e3da; margin: 2rem 0; }
.cc-brief-doc strong { color: #1a1a1a; }
.cc-brief-doc table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0 1.5rem;
    font-size: 0.85rem;
}
.cc-brief-doc table th {
    background: #1a1a1a !important;
    color: #c9a96e !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.63rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 0.75rem !important;
    text-align: left !important;
    border: 1px solid #1a1a1a !important;
}
.cc-brief-doc table td {
    padding: 0.5rem 0.75rem !important;
    color: #2a2a2a !important;
    border: 1px solid #e6e3da !important;
    background: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
}
.cc-brief-doc table tr:nth-child(even) td {
    background: #f5f3ee !important;
}

/* ---------- Tables ---------- */
[data-testid="stDataFrame"] {
    border: 1px solid #1a1a1a;
    border-radius: 0;
}
[data-testid="stDataFrame"] thead tr th {
    background: #1a1a1a !important;
    color: #c9a96e !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
}

/* ---------- Misc ---------- */
.cc-divider {
    border: none;
    border-top: 1px solid #e6e3da;
    margin: 1.6rem 0;
}
.cc-divider-heavy {
    border: none;
    border-top: 1px solid #1a1a1a;
    margin: 1.8rem 0;
}
[data-testid="stMetricLabel"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.62rem !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: #888 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 1.9rem !important;
    color: #1a1a1a !important;
}
.stExpander { border: 1px solid #e6e3da !important; border-radius: 0 !important; background: #fff !important; }
.stExpander [data-testid="stExpanderDetails"] { background: #fff !important; color: #1a1a1a !important; }
.stExpander [data-testid="stExpanderDetails"] p,
.stExpander [data-testid="stExpanderDetails"] span,
.stExpander [data-testid="stExpanderDetails"] div { color: #1a1a1a !important; }
.stExpander [data-testid="stExpanderDetails"] a { color: #1a1a1a !important; }
[data-testid="stSidebar"] .stExpander { background: #242424 !important; border: 1px solid #333 !important; }
[data-testid="stSidebar"] .stExpander summary,
[data-testid="stSidebar"] .stExpander summary p,
[data-testid="stSidebar"] .stExpander summary span,
[data-testid="stSidebar"] .stExpander [data-testid="stExpanderToggleIcon"] svg { color: #c9a96e !important; fill: #c9a96e !important; }
[data-testid="stSidebar"] .stExpander [data-testid="stExpanderDetails"] p,
[data-testid="stSidebar"] .stExpander [data-testid="stExpanderDetails"] li,
[data-testid="stSidebar"] .stExpander [data-testid="stExpanderDetails"] code { color: #e8e6df !important; background: transparent !important; }
[data-testid="stSidebar"] .stExpander [data-testid="stExpanderDetails"] strong { color: #c9a96e !important; }

/* Brand badge */
.brand-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: white;
    margin-right: 6px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

BRANDS = ["Chanel", "Dior", "Gucci"]
BRAND_COLORS = {"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"}
EVENT_TYPES = [
    "collection_launch", "campaign_or_collaboration", "pricing_or_exclusivity",
    "geographic_expansion", "creative_direction", "sustainability_or_sourcing",
    "celebrity_or_influencer_alignment", "reputational_issue",
]
SENTIMENT_EMOJI = {
    "positive": "○", "very_positive": "●",
    "negative": "△", "very_negative": "▲",
    "neutral": "—",
}

# Plotly theme — Bloomberg-on-black with gold accents
PLOTLY_DARK = dict(
    paper_bgcolor="#1a1a1a",
    plot_bgcolor="#1a1a1a",
    font=dict(family="Inter, sans-serif", color="#e8e6df", size=12),
    title=dict(text="", font=dict(family="Cormorant Garamond, serif", color="#ffffff", size=18)),
    xaxis=dict(
        gridcolor="#2a2a2a", linecolor="#3a3a3a", zerolinecolor="#3a3a3a",
        tickfont=dict(color="#a8a59c", size=10),
        title=dict(font=dict(color="#c9a96e", size=11)),
    ),
    yaxis=dict(
        gridcolor="#2a2a2a", linecolor="#3a3a3a", zerolinecolor="#3a3a3a",
        tickfont=dict(color="#a8a59c", size=10),
        title=dict(font=dict(color="#c9a96e", size=11)),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8e6df", size=10),
        bordercolor="#3a3a3a",
    ),
    margin=dict(l=40, r=20, t=50, b=40),
)

# Muted/gold-leaning brand palette for charts on dark
CHART_BRANDS = {"Chanel": "#c9a96e", "Dior": "#a87b5c", "Gucci": "#7a8a5a"}

# ──────────────────────────────────────────────
# Data loaders (UNCHANGED)
# ──────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_events(days: int = 30, brands: list = None, event_types: list = None) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT
            i.item_id, i.competitor, i.source_name, i.source_url, i.source_type,
            i.published_at, i.title, i.official_source,
            i.sentiment_label, i.sentiment_score, i.sentiment_confidence,
            e.event_type, e.business_function, e.relevance_score,
            e.impact_score, e.summary, e.evidence_snippet,
            e.confidence_score, e.cluster_id
        FROM items i
        LEFT JOIN events e ON i.item_id = e.item_id
        WHERE i.published_at >= datetime('now', ?)
        ORDER BY i.published_at DESC
    """
    df = pd.read_sql_query(query, conn, params=(f"-{days} days",))
    conn.close()
    if brands:
        df = df[df["competitor"].isin(brands)]
    if event_types:
        df = df[df["event_type"].isin(event_types)]
    return df


@st.cache_data(ttl=300)
def load_corpus() -> list[dict]:
    """Return all items with embeddings plus display fields for semantic search."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.item_id, i.competitor, i.title, i.excerpt, i.published_at,
               i.source_name, i.source_url, i.embedding
        FROM items i
        WHERE i.embedding IS NOT NULL
    """).fetchall()
    conn.close()
    corpus = []
    for r in rows:
        row = dict(r)
        emb_bytes = row.pop("embedding")
        row["embedding"] = from_bytes(emb_bytes)
        corpus.append(row)
    return corpus


@st.cache_data(ttl=300)
def load_trends() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM trends ORDER BY trend_score DESC", conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_critical_event_details() -> dict:
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.competitor, e.event_type, e.impact_score, e.evidence_snippet,
               i.title, i.source_name, i.source_url, i.published_at
        FROM events e
        JOIN items i ON e.item_id = i.item_id
        ORDER BY e.impact_score DESC
    """).fetchall()
    conn.close()
    seen = {}
    for r in rows:
        key = (r["competitor"], r["event_type"])
        if key not in seen:
            seen[key] = dict(r)
    return seen


@st.cache_data(ttl=300)
def load_x_posts(days: int = 30) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT item_id, competitor, source_name, source_url,
               published_at, excerpt, raw_text,
               sentiment_label, sentiment_score, engagement_metrics
        FROM items
        WHERE source_name LIKE 'X - @%'
          AND published_at >= datetime('now', ?)
        ORDER BY published_at DESC
    """, conn, params=(f"-{days} days",))
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_brand_vectors() -> pd.DataFrame:
    """
    Compute weekly brand centroids from stored article embeddings.
    Returns a DataFrame with columns: brand, week, centroid (numpy array),
    plus a flat embedding stored as a list for caching compatibility.
    """
    from src.processing.embeddings import from_bytes
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.competitor, i.published_at, i.embedding
        FROM items i
        WHERE i.embedding IS NOT NULL AND i.competitor IS NOT NULL
        ORDER BY i.published_at
    """).fetchall()
    conn.close()

    records = []
    for r in rows:
        try:
            emb = from_bytes(r["embedding"])
            pub = pd.to_datetime(r["published_at"], errors="coerce", utc=True)
            if pub is pd.NaT or emb is None:
                continue
            week = pub.to_period("W").start_time
            records.append({"brand": r["competitor"], "week": week, "emb": emb})
        except Exception:
            continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Compute centroid per (brand, week)
    centroids = []
    for (brand, week), grp in df.groupby(["brand", "week"]):
        matrix = np.stack(grp["emb"].tolist())
        centroid = matrix.mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        centroids.append({"brand": brand, "week": week, "centroid": centroid.tolist(), "n": len(grp)})
    return pd.DataFrame(centroids)


@st.cache_data(ttl=300)
def load_brief() -> str:
    briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True)
    if files:
        return files[0].read_text(encoding="utf-8")
    return "_No brief generated yet. Run the pipeline first._"


def _brief_to_pdf(markdown_text: str) -> bytes:
    """Render the markdown brief as a PDF and return raw bytes."""
    from fpdf import FPDF

    class BriefPDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(180, 150, 100)
            self.cell(0, 8, "C&C INTELLIGENCE  ·  CONFIDENTIAL", align="C")
            self.ln(2)
            self.set_draw_color(26, 26, 26)
            self.set_line_width(0.4)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f"Page {self.page_no()} / {{nb}}", align="C")

    pdf = BriefPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(left=22, top=18, right=22)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    _H1 = re.compile(r"^#\s+(.*)")
    _H2 = re.compile(r"^##\s+(.*)")
    _H3 = re.compile(r"^###\s+(.*)")
    _HR = re.compile(r"^---+$")
    _BOLD = re.compile(r"\*\*(.+?)\*\*")

    def _strip_md(text: str) -> str:
        text = _BOLD.sub(r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = text.replace("—", "--").replace("–", "-").replace("•", "-")
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        return text.strip()

    for line in markdown_text.splitlines():
        m1 = _H1.match(line)
        m2 = _H2.match(line)
        m3 = _H3.match(line)

        if m1:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(26, 26, 26)
            pdf.multi_cell(0, 9, _strip_md(m1.group(1)))
            pdf.set_x(pdf.l_margin)
            pdf.ln(1)
        elif m2:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(26, 26, 26)
            pdf.multi_cell(0, 7, _strip_md(m2.group(1)))
            pdf.set_x(pdf.l_margin)
            pdf.set_draw_color(230, 227, 218)
            pdf.set_line_width(0.2)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
        elif m3:
            pdf.ln(3)
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(181, 147, 108)
            pdf.multi_cell(0, 6, _strip_md(m3.group(1)))
            pdf.set_x(pdf.l_margin)
            pdf.ln(1)
        elif _HR.match(line.strip()):
            pdf.ln(2)
            pdf.set_draw_color(200, 195, 180)
            pdf.set_line_width(0.2)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
        elif line.strip().startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(44, 44, 44)
            pdf.multi_cell(0, 5.5, "  - " + _strip_md(line.strip()[2:]))
            pdf.set_x(pdf.l_margin)
        elif line.strip():
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(44, 44, 44)
            pdf.multi_cell(0, 5.5, _strip_md(line))
            pdf.set_x(pdf.l_margin)
        else:
            pdf.ln(2)

    return bytes(pdf.output())


def _last_updated_string() -> str:
    """Latest brief file timestamp, or 'never'."""
    briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True)
    if not files:
        return "Never"
    try:
        ts = datetime.fromtimestamp(files[0].stat().st_mtime, tz=timezone.utc)
        return ts.strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        return "—"


def _impact_bar(score: float) -> str:
    """Render a 5-segment bar HTML for impact score."""
    score = score or 0
    filled = max(0, min(5, int(round(score))))
    return "".join(f'<span class="{"on" if i < filled else ""}"></span>' for i in range(5))


def _esc(text) -> str:
    if text is None:
        return ""
    return str(text).replace("<", "&lt;").replace(">", "&gt;")


# ──────────────────────────────────────────────
# Sidebar — brand mark, status, filters, pipeline
# ──────────────────────────────────────────────

st.sidebar.markdown("""
<div class="cc-logo">
    <div class="mark">C<span class="amp">&</span>C</div>
    <div class="tag">Competitive Intelligence</div>
</div>
""", unsafe_allow_html=True)

last_updated = _last_updated_string()
st.sidebar.markdown(f"""
<div class="cc-status">
    <div class="label">Last Updated</div>
    <div class="value"><span class="pulse"></span>{last_updated}</div>
</div>
""", unsafe_allow_html=True)

run_clicked = st.sidebar.button("Run Pipeline", type="primary", key="run_pipeline_btn")
reload_clicked = st.sidebar.button("Reload Dashboard", key="reload_btn")

if run_clicked:
    with st.spinner("Running pipeline… this may take a few minutes"):
        try:
            from src.pipeline import run_pipeline
            run_pipeline()
            st.cache_data.clear()
            st.sidebar.success("Pipeline complete.")
        except Exception as e:
            st.sidebar.error(f"Pipeline error: {e}")

if reload_clicked:
    st.cache_data.clear()
    st.session_state["filter_brands"] = BRANDS
    st.session_state["filter_types"] = EVENT_TYPES
    st.session_state["filter_days"] = 30

st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

selected_brands = st.sidebar.multiselect("Brands", BRANDS, default=BRANDS, key="filter_brands")
selected_types = st.sidebar.multiselect("Event Types", EVENT_TYPES, default=EVENT_TYPES, key="filter_types")
days_back = st.sidebar.slider("Time Window (days)", 7, 30, 30, key="filter_days")

st.sidebar.markdown("<hr/>", unsafe_allow_html=True)

with st.sidebar.expander("Methodology"):
    st.markdown("""
**Impact** (1–5) — Significance of the event for the brand's market position. `1` minor mention · `5` market-moving.

**Relevance** (0–1) — Closeness to luxury fashion competitive intelligence. `0.8+` highly on-topic.

**Confidence** (0–1) — Classifier certainty in event-type assignment. `0.7+` reliable.

**Trend Score** — `0.5 × burst_z + 0.3 × log(1+sources) + 0.2 × (impact/5)`. Higher = unusual spike vs 28-day baseline.
""")

# ──────────────────────────────────────────────
# Masthead
# ──────────────────────────────────────────────

now_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y").upper()
edition_str = datetime.now(timezone.utc).strftime("VOL. %y · NO. %j")

st.markdown(f"""
<div class="cc-masthead">
    <div class="topline">
        <span>{now_str}</span>
        <span>The Competitive Edition</span>
        <span class="right">{edition_str}</span>
    </div>
    <h1>Chanel <em>&amp;</em> The Houses</h1>
    <div class="dek">A daily intelligence dossier on Dior, Gucci, and the broader luxury landscape — assembled from press, social, and brand channels.</div>
</div>
""", unsafe_allow_html=True)

init_db()

df_events = load_events(days=days_back, brands=selected_brands, event_types=selected_types)
df_trends = load_trends()

# ── KPI strip ──
events_extracted = int(df_events["event_type"].notna().sum()) if not df_events.empty else 0
trends_count = len(df_trends)
critical_count = int(df_trends["is_critical"].sum()) if not df_trends.empty else 0

avg_sentiment_str = "N/A"
if not df_events.empty and "sentiment_score" in df_events.columns:
    avg_sentiment = df_events["sentiment_score"].mean()
    if pd.notna(avg_sentiment):
        avg_sentiment_str = f"{avg_sentiment:+.2f}"

avg_impact_str = "N/A"
df_competitors = df_events[df_events["competitor"].isin(["Dior", "Gucci"])] if not df_events.empty else pd.DataFrame()
if not df_competitors.empty and "impact_score" in df_competitors.columns:
    avg_impact = df_competitors["impact_score"].dropna().mean()
    if pd.notna(avg_impact):
        avg_impact_str = f"{avg_impact:.1f} / 5"

st.markdown(f"""
<div class="cc-kpi-strip">
    <div class="cc-kpi"><div class="label">Events</div><div class="value">{events_extracted:,}</div><div class="delta">EXTRACTED</div></div>
    <div class="cc-kpi gold"><div class="label">Trends</div><div class="value">{trends_count}</div><div class="delta">DETECTED</div></div>
    <div class="cc-kpi alert"><div class="label">Critical</div><div class="value">{critical_count}</div><div class="delta">FLAGGED</div></div>
    <div class="cc-kpi"><div class="label">Sentiment</div><div class="value">{avg_sentiment_str}</div><div class="delta">AVG SCORE</div></div>
    <div class="cc-kpi gold"><div class="label">Comp. Impact</div><div class="value">{avg_impact_str}</div><div class="delta">DIOR + GUCCI</div></div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──
tab_brief, tab_digest, tab_trends, tab_perception, tab_compare, tab_moves, tab_search = st.tabs([
    "Weekly Brief",
    "Digest",
    "Trends",
    "Perception",
    "Compare",
    "Event Feed",
    "Search",
])

# ─── Tab 1: Digest ────────────────────────────────────────────
with tab_digest:
    st.markdown('<div class="cc-section-eyebrow">The Front Page</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Intelligence Digest</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">What happened this week — critical alerts, top competitor moves, and competitive positioning at a glance.</div>', unsafe_allow_html=True)

    # A. Critical Events
    df_critical = df_trends[df_trends["is_critical"] == 1].sort_values("trend_score", ascending=False).head(5) if not df_trends.empty else pd.DataFrame()

    if not df_critical.empty:
        st.markdown('<div class="cc-section-eyebrow" style="color:#b8463f;">Critical Alerts</div>', unsafe_allow_html=True)
        critical_details = load_critical_event_details()
        for _, row in df_critical.iterrows():
            event_label = str(row.get("event_type", "")).replace("_", " ").title()
            competitor = row.get("competitor", "Unknown")
            impact = row.get("avg_impact", 0)
            count = row.get("count_7d", 0)
            detail = critical_details.get((competitor, row.get("event_type", "")), {})
            art_title = _esc(str(detail.get("title", "") or "")[:120])
            snippet = _esc(str(detail.get("evidence_snippet", "") or "")[:220])
            source = _esc(str(detail.get("source_name", "") or ""))
            url = str(detail.get("source_url", "") or "")
            date = str(detail.get("published_at", "") or "")[:10]
            title_html = f'<a href="{url}" target="_blank">{art_title}</a>' if url and art_title else art_title
            st.markdown(f"""
<div class="cc-critical">
  <div class="cc-critical-body">
    <div class="label">▲ Critical Trend</div>
    <div class="headline"><span class="brand">{_esc(competitor)}</span>{_esc(event_label)}</div>
    {f'<div class="cc-critical-title">{title_html}</div>' if art_title else ''}
    {f'<div class="cc-critical-snippet">{snippet}</div>' if snippet else ''}
    <div class="cc-critical-footer">
      <span>{source}{(' · ' + date) if date else ''}</span>
      <span>{impact:.1f}/5 IMPACT · {count} ARTICLES</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:1rem;border-left:2px solid #c9a96e;background:#fff;color:#555;font-size:0.9rem;">No critical events detected in this window.</div>', unsafe_allow_html=True)

    st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)

    # B. Two-column: Moves + Trending
    col_moves, col_trending = st.columns([1.3, 1])

    with col_moves:
        st.markdown('<div class="cc-section-eyebrow">Competitor Desk</div>', unsafe_allow_html=True)
        st.markdown('<div class="cc-section-title" style="font-size:1.4rem;">Top Moves</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.05em;margin-bottom:0.7rem;">By impact · Dior &amp; Gucci · last {} days</div>'.format(days_back), unsafe_allow_html=True)

        df_comp_moves = (
            df_events[df_events["competitor"].isin(["Dior", "Gucci"]) & df_events["event_type"].notna()]
            .sort_values("impact_score", ascending=False)
            .head(5)
        ) if not df_events.empty else pd.DataFrame()

        if df_comp_moves.empty:
            st.markdown('<div style="color:#888;font-size:0.85rem;">No competitor events found.</div>', unsafe_allow_html=True)
        else:
            for _, row in df_comp_moves.iterrows():
                event_label = str(row.get("event_type", "")).replace("_", " ").title()
                title = _esc(str(row.get("title", ""))[:120])
                impact = row.get("impact_score") or 0
                source = _esc(row.get("source_name", ""))
                url = row.get("source_url", "")
                date = str(row.get("published_at", ""))[:10]
                title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
                st.markdown(f"""
<div class="cc-feed-item">
  <div class="cc-feed-meta">
    <div class="date">{date}</div>
    <div style="margin-top:0.15rem;">IMPACT {impact:.1f}</div>
    <div class="impact-bar">{_impact_bar(impact)}</div>
  </div>
  <div class="cc-feed-body">
    <span class="brand">{_esc(row['competitor'])}</span>
    <span class="etype">{_esc(event_label)}</span>
    <h3>{title_html}</h3>
    <div class="source-line">{source}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    with col_trending:
        st.markdown('<div class="cc-section-eyebrow">Signal Watch</div>', unsafe_allow_html=True)
        st.markdown('<div class="cc-section-title" style="font-size:1.4rem;">Trending</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.05em;margin-bottom:0.7rem;">Top signals by trend score</div>', unsafe_allow_html=True)

        df_top_trends = df_trends.head(5) if not df_trends.empty else pd.DataFrame()

        if df_top_trends.empty:
            st.markdown('<div style="color:#888;font-size:0.85rem;">No trends detected yet.</div>', unsafe_allow_html=True)
        else:
            for _, row in df_top_trends.iterrows():
                event_label = str(row.get("event_type", "")).replace("_", " ").title()
                competitor = row.get("competitor", "")
                score = row.get("trend_score", 0)
                count = row.get("count_7d", 0)
                sources = row.get("unique_sources_7d") or row.get("unique_sources", 0)
                bar_pct = min(int(score / 5 * 100), 100)
                st.markdown(f"""
<div class="cc-trend">
  <div class="row1">
    <div class="label"><span class="brand">{_esc(competitor)}</span> {_esc(event_label)}</div>
    <div class="score">{score:.2f}</div>
  </div>
  <div class="bar"><div style="width:{bar_pct}%"></div></div>
  <div class="meta">{count} articles · {sources} sources</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="cc-divider-heavy"/>', unsafe_allow_html=True)

    # C. Heatmap (dark)
    st.markdown('<div class="cc-section-eyebrow">Market Map</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title" style="font-size:1.4rem;">Competitive Activity</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.05em;margin-bottom:0.7rem;">Article volume by event type and brand</div>', unsafe_allow_html=True)

    if not df_events.empty and "event_type" in df_events.columns:
        df_hm = df_events[df_events["event_type"].notna()].copy()
        df_hm["event_type_label"] = df_hm["event_type"].str.replace("_", " ").str.title()
        pivot = df_hm.pivot_table(index="event_type_label", columns="competitor",
                                  values="item_id", aggfunc="nunique", fill_value=0)
        for b in BRANDS:
            if b not in pivot.columns:
                pivot[b] = 0
        pivot = pivot[BRANDS]

        fig_hm = go.Figure(go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0, "#1a1a1a"], [0.5, "#5a4a30"], [1, "#c9a96e"]],
            text=[[str(v) for v in row] for row in pivot.values.tolist()],
            texttemplate="%{text}",
            textfont=dict(color="#fafaf7", family="JetBrains Mono"),
            showscale=True,
            colorbar=dict(tickfont=dict(color="#a8a59c"), outlinecolor="#3a3a3a"),
            hovertemplate="<b>%{y}</b><br>%{x}: %{z} articles<extra></extra>",
        ))
        fig_hm.update_layout(height=420, **PLOTLY_DARK)
        fig_hm.update_layout(margin=dict(l=10, r=20, t=10, b=10))
        fig_hm.update_yaxes(automargin=True)
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.markdown('<div style="color:#888;font-size:0.85rem;">Run the pipeline to populate the heatmap.</div>', unsafe_allow_html=True)


# ─── Tab 2: Event Feed (was Competitor Moves) ────────────────
with tab_moves:
    st.markdown('<div class="cc-section-eyebrow">Live Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Event Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Every classified event in the window — sorted by impact, presented as a news feed.</div>', unsafe_allow_html=True)

    if df_events.empty:
        st.markdown('<div style="color:#888;font-size:0.9rem;">No events found. Run the pipeline to ingest data.</div>', unsafe_allow_html=True)
    else:
        df_sorted = df_events[df_events["event_type"].notna()].sort_values("impact_score", ascending=False).copy()

        # Sort selector
        col_a, col_b, col_c = st.columns([1, 1, 4])
        with col_a:
            sort_by = st.selectbox("Sort", ["Impact", "Date", "Relevance", "Confidence"], label_visibility="collapsed")
        with col_b:
            view_mode = st.selectbox("View", ["Feed", "Table"], label_visibility="collapsed")

        sort_key = {"Impact": "impact_score", "Date": "published_at",
                    "Relevance": "relevance_score", "Confidence": "confidence_score"}[sort_by]
        df_sorted = df_sorted.sort_values(sort_key, ascending=False)

        if view_mode == "Feed":
            # News-feed presentation
            st.markdown('<div class="cc-feed">', unsafe_allow_html=True)
            for _, row in df_sorted.head(40).iterrows():
                event_label = str(row.get("event_type", "")).replace("_", " ").title()
                title = _esc(str(row.get("title", "")))
                summary = _esc(str(row.get("summary", "") or ""))[:280]
                if summary and len(str(row.get("summary", "") or "")) > 280:
                    summary += "…"
                impact = row.get("impact_score") or 0
                relevance = row.get("relevance_score") or 0
                source = _esc(row.get("source_name", ""))
                url = row.get("source_url", "")
                official = bool(row.get("official_source"))
                date_dt = pd.to_datetime(row.get("published_at"), errors="coerce")
                date_str = date_dt.strftime("%d %b").upper() if pd.notna(date_dt) else ""
                year_str = date_dt.strftime("%Y") if pd.notna(date_dt) else ""
                title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
                official_html = '<span class="official">Official</span>' if official else ""
                sentiment_label = row.get("sentiment_label") or "neutral"
                sent_score = row.get("sentiment_score")
                sent_html = ""
                if sent_score is not None and pd.notna(sent_score):
                    sent_color = "#5a8a5a" if sent_score > 0.2 else ("#b8463f" if sent_score < -0.2 else "#888")
                    sent_html = f' · <span style="color:{sent_color};">SENT {sent_score:+.2f}</span>'

                st.markdown(f"""
<div class="cc-feed-item">
  <div class="cc-feed-meta">
    <div class="date">{date_str}</div>
    <div style="color:#aaa">{year_str}</div>
    <div style="margin-top:0.5rem;">IMPACT {impact:.1f}</div>
    <div class="impact-bar">{_impact_bar(impact)}</div>
    <div style="margin-top:0.5rem;">REL {relevance:.2f}</div>
  </div>
  <div class="cc-feed-body">
    <span class="brand">{_esc(row['competitor'])}</span>
    <span class="etype">{_esc(event_label)}</span>
    <h3>{title_html}</h3>
    <div class="summary">{summary}</div>
    <div class="source-line">{source}{official_html}{sent_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if len(df_sorted) > 40:
                st.markdown(f'<div style="text-align:center;color:#888;font-family:JetBrains Mono;font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;padding:1.5rem 0;border-top:1px solid #e6e3da;">Showing 40 of {len(df_sorted)} events · switch to Table view to see all</div>', unsafe_allow_html=True)
        else:
            # Table fallback
            def _truncate(text, n=120):
                s = str(text) if pd.notna(text) else ""
                return s[:n] + "…" if len(s) > n else s

            df_sorted["summary_short"] = df_sorted["summary"].apply(lambda x: _truncate(x, 120))
            df_sorted["event_type_label"] = df_sorted["event_type"].str.replace("_", " ").str.title()
            df_sorted["business_function_label"] = df_sorted["business_function"].fillna("—")
            df_sorted["published_at_fmt"] = pd.to_datetime(df_sorted["published_at"], errors="coerce").dt.strftime("%Y-%m-%d")
            df_sorted["official_flag"] = df_sorted["official_source"].map({1: "✓", 0: ""})
            df_sorted["sentiment_emoji"] = df_sorted["sentiment_label"].fillna("neutral").map(SENTIMENT_EMOJI).fillna("—")

            display_cols = [
                "published_at_fmt", "competitor", "event_type_label", "business_function_label",
                "title", "summary_short", "impact_score", "relevance_score", "confidence_score",
                "sentiment_emoji", "sentiment_score", "source_name", "official_flag",
            ]
            df_disp = df_sorted[display_cols].rename(columns={
                "published_at_fmt": "Date", "competitor": "Brand",
                "event_type_label": "Event Type", "business_function_label": "Function",
                "title": "Title", "summary_short": "Summary",
                "impact_score": "Impact", "relevance_score": "Relevance",
                "confidence_score": "Confidence", "sentiment_emoji": "Sent.",
                "sentiment_score": "Sent. Score", "source_name": "Source",
                "official_flag": "Official",
            })
            st.dataframe(
                df_disp, use_container_width=True, height=560,
                column_config={
                    "Impact": st.column_config.NumberColumn(format="%.1f", min_value=1, max_value=5),
                    "Relevance": st.column_config.NumberColumn(format="%.2f"),
                    "Confidence": st.column_config.NumberColumn(format="%.2f"),
                    "Sent. Score": st.column_config.NumberColumn(format="%.2f", min_value=-1, max_value=1),
                },
            )

        # Evidence
        with st.expander("Evidence snippets — top 10"):
            for _, row in df_sorted.head(10).iterrows():
                if row.get("evidence_snippet"):
                    event_label = str(row.get("event_type", "")).replace("_", " ").title()
                    st.markdown(f"**{row['competitor']} · {event_label}**")
                    st.caption(row["evidence_snippet"])
                    if row.get("source_url"):
                        st.markdown(f"[Source]({row['source_url']})")
                    st.divider()


# ─── Tab 3: Trends ───────────────────────────────────────────
with tab_trends:
    st.markdown('<div class="cc-section-eyebrow">Quantitative Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Trends &amp; Signals</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Burst-detected event types ranked by trend score against the 28-day baseline.</div>', unsafe_allow_html=True)

    if df_trends.empty:
        st.markdown('<div style="color:#888;font-size:0.9rem;">No trends detected yet. Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        df_t = df_trends.copy()
        df_t["event_type_label"] = df_t["event_type"].str.replace("_", " ").str.title()

        fig_bar = px.bar(
            df_t.head(15),
            x="trend_score", y="event_type_label",
            color="competitor", orientation="h", barmode="group",
            labels={"trend_score": "Trend Score", "event_type_label": "Event Type", "competitor": "Brand"},
            color_discrete_map=CHART_BRANDS,
        )
        fig_bar.update_layout(height=440, **PLOTLY_DARK)
        fig_bar.update_layout(title=dict(text="Top 15 Trend Scores", x=0.01))
        st.plotly_chart(fig_bar, use_container_width=True)

        fig_scatter = px.scatter(
            df_t,
            x="burst_z", y="avg_impact", size="count_7d",
            color="competitor",
            hover_data=["event_type_label", "unique_sources", "trend_score"],
            labels={"burst_z": "Burst Z-Score", "avg_impact": "Avg Impact", "competitor": "Brand"},
            color_discrete_map=CHART_BRANDS,
        )
        fig_scatter.update_layout(height=380, **PLOTLY_DARK)
        fig_scatter.update_layout(title=dict(text="Burst Intensity × Average Impact", x=0.01))
        fig_scatter.update_traces(marker=dict(line=dict(color="#1a1a1a", width=1)))
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.04em;margin:-0.5rem 0 1rem;">Bubble = articles in last 7 days. Upper-right = high burst + high impact.</div>', unsafe_allow_html=True)

        # Time-series: daily signal volume per brand over the last 14 days
        if not df_events.empty and "published_at" in df_events.columns:
            df_ts = df_events.copy()
            df_ts["date"] = pd.to_datetime(df_ts["published_at"], errors="coerce").dt.normalize()
            cutoff = pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=14)
            df_ts = df_ts[df_ts["date"] >= cutoff]
            if not df_ts.empty:
                daily = (
                    df_ts.groupby(["date", "competitor"])["item_id"]
                    .nunique()
                    .reset_index(name="articles")
                )
                # Fill date gaps with 0 so lines are continuous
                all_dates = pd.date_range(cutoff, pd.Timestamp.now(tz="UTC").normalize(), freq="D")
                all_combos = pd.MultiIndex.from_product(
                    [all_dates, daily["competitor"].unique()], names=["date", "competitor"]
                )
                daily = (
                    daily.set_index(["date", "competitor"])
                    .reindex(all_combos, fill_value=0)
                    .reset_index()
                )
                fig_ts = px.line(
                    daily, x="date", y="articles", color="competitor",
                    labels={"date": "Date", "articles": "Articles", "competitor": "Brand"},
                    color_discrete_map=CHART_BRANDS,
                )
                fig_ts.update_layout(height=320, **PLOTLY_DARK)
                fig_ts.update_layout(title=dict(text="Signal Volume — Last 14 Days", x=0.01))
                fig_ts.update_traces(line=dict(width=2))
                st.plotly_chart(fig_ts, use_container_width=True)

        table_cols = ["competitor", "event_type_label", "trend_score", "count_7d",
                      "unique_sources", "avg_impact", "is_critical"]
        rename_map = {
            "competitor": "Brand", "event_type_label": "Event Type",
            "trend_score": "Score", "count_7d": "7d Articles",
            "unique_sources": "Sources", "avg_impact": "Avg Impact",
            "is_critical": "Status",
        }
        if "anomaly_score" in df_t.columns and df_t["anomaly_score"].notna().any():
            table_cols.append("anomaly_score")
            rename_map["anomaly_score"] = "Anomaly ↑"
        df_table = df_t[table_cols].copy()
        df_table["is_critical"] = df_table["is_critical"].apply(lambda v: "● Critical" if v else "")
        st.dataframe(
            df_table.rename(columns=rename_map),
            use_container_width=True, hide_index=True,
        )
        if "anomaly_score" in df_t.columns and df_t["anomaly_score"].notna().any():
            st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.04em;margin:-0.4rem 0 0.5rem;">Anomaly ↑ — IsolationForest score (0–1). Higher = more statistically unusual versus other trends.</div>', unsafe_allow_html=True)

        # ── Trend drill-down ──────────────────────────────────────
        st.markdown('<div class="cc-section-eyebrow" style="margin-top:1.5rem;">Drill Down</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.82rem;color:#888;margin-bottom:0.8rem;">Expand any trend to see the underlying articles driving the signal.</div>', unsafe_allow_html=True)

        for _, trow in df_t.iterrows():
            brand = trow["competitor"]
            etype = trow["event_type"]
            elabel = trow["event_type_label"]
            score = trow["trend_score"]
            critical_badge = " ● Critical" if trow.get("is_critical") else ""
            expander_label = f"{brand} — {elabel}  (score {score:.2f}){critical_badge}"

            if not df_events.empty:
                mask = (df_events["competitor"] == brand) & (df_events["event_type"] == etype)
                articles = df_events[mask].sort_values("impact_score", ascending=False).head(10)
            else:
                articles = pd.DataFrame()

            with st.expander(expander_label):
                if articles.empty:
                    st.markdown("_No articles found for this trend in the current date window._")
                else:
                    for _, art in articles.iterrows():
                        sent_label = art.get("sentiment_label") or ""
                        sent_color = {"positive": "#5a7a4e", "negative": "#c0392b", "neutral": "#888"}.get(sent_label, "#888")
                        impact = art.get("impact_score")
                        impact_str = f"Impact {impact:.1f}" if impact else ""
                        date_str = str(art.get("published_at", ""))[:10]
                        source = art.get("source_name", "")
                        url = art.get("source_url", "")
                        title = art.get("title") or art.get("summary") or "Untitled"
                        snippet = art.get("evidence_snippet") or ""

                        title_md = f"[{title}]({url})" if url else title
                        meta = " · ".join(filter(None, [date_str, source, impact_str]))
                        sent_md = f'<span style="color:{sent_color};font-size:0.75rem;font-weight:600;">{sent_label.upper()}</span>' if sent_label else ""
                        st.markdown(
                            f'<div style="border-left:3px solid #c9a96e;padding:0.5rem 0.75rem;margin-bottom:0.6rem;background:#fafaf7;">'
                            f'<div style="font-size:0.88rem;font-weight:600;color:#1a1a1a;">{title_md}</div>'
                            f'<div style="font-size:0.75rem;color:#666;margin:0.2rem 0;">{meta} {sent_md}</div>'
                            f'<div style="font-size:0.8rem;color:#444;">{snippet}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )


# ─── Tab 4: Perception ───────────────────────────────────────
with tab_perception:
    st.markdown('<div class="cc-section-eyebrow">Public Voice</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Brand Perception</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Sentiment across press and social channels — quantified, ranked, and contextualised.</div>', unsafe_allow_html=True)

    if df_events.empty or "sentiment_label" not in df_events.columns or df_events["sentiment_label"].isna().all():
        st.markdown('<div style="color:#888;font-size:0.9rem;">Sentiment data not yet available. Run the pipeline.</div>', unsafe_allow_html=True)
    else:
        df_sent = df_events[df_events["sentiment_label"].notna()].copy()
        if not df_sent.empty:
            col1, col2, col3, col4 = st.columns(4)
            positive_pct = df_sent["sentiment_label"].isin(["positive", "very_positive"]).sum() / len(df_sent) * 100
            negative_pct = df_sent["sentiment_label"].isin(["negative", "very_negative"]).sum() / len(df_sent) * 100
            neutral_pct = (df_sent["sentiment_label"] == "neutral").sum() / len(df_sent) * 100
            avg_sent = df_sent["sentiment_score"].mean()
            col1.metric("Positive", f"{positive_pct:.1f}%")
            col2.metric("Negative", f"{negative_pct:.1f}%")
            col3.metric("Neutral", f"{neutral_pct:.1f}%")
            col4.metric("Avg Score", f"{avg_sent:+.2f}")

            col_bar, col_pie = st.columns(2)
            with col_bar:
                brand_sent = df_sent.groupby("competitor")["sentiment_score"].mean().reset_index()
                brand_sent.columns = ["Brand", "Avg Sentiment"]
                fig_brand_sent = px.bar(
                    brand_sent, x="Brand", y="Avg Sentiment", color="Brand",
                    text="Avg Sentiment", color_discrete_map=CHART_BRANDS,
                )
                fig_brand_sent.update_traces(texttemplate="%{text:+.1%}", textposition="outside",
                                             textfont=dict(color="#e8e6df"))
                fig_brand_sent.add_hline(y=0, line_dash="dash", line_color="#3a3a3a")
                fig_brand_sent.update_layout(height=340, showlegend=False, **PLOTLY_DARK)
                fig_brand_sent.update_layout(title=dict(text="Avg Sentiment by Brand", x=0.01))
                fig_brand_sent.update_yaxes(title_text="Avg Sentiment (%)", tickformat=".0%")
                st.plotly_chart(fig_brand_sent, use_container_width=True)

            with col_pie:
                sentiment_counts = df_sent["sentiment_label"].value_counts().reset_index()
                sentiment_counts.columns = ["Sentiment", "Count"]
                fig_pie = px.pie(
                    sentiment_counts, names="Sentiment", values="Count",
                    color="Sentiment", hole=0.5,
                    color_discrete_map={
                        "positive": "#a89066", "very_positive": "#c9a96e",
                        "neutral": "#5a5a55", "negative": "#7a4a3a", "very_negative": "#b8463f",
                    },
                )
                fig_pie.update_traces(texttemplate="%{label}<br>%{percent:.0%}",
                                      textfont=dict(color="#e8e6df"),
                                      marker=dict(line=dict(color="#1a1a1a", width=2)))
                fig_pie.update_layout(height=340, **PLOTLY_DARK)
                fig_pie.update_layout(title=dict(text="Sentiment Distribution", x=0.01))
                st.plotly_chart(fig_pie, use_container_width=True)

            # Diverging bar: positive vs negative share-of-voice per brand
            brand_labels = sorted(df_sent["competitor"].unique())
            pos_shares, neg_shares, neu_shares = [], [], []
            for b in brand_labels:
                sub = df_sent[df_sent["competitor"] == b]
                n = len(sub)
                pos_shares.append(sub["sentiment_label"].isin(["positive", "very_positive"]).sum() / n * 100)
                neg_shares.append(-sub["sentiment_label"].isin(["negative", "very_negative"]).sum() / n * 100)
                neu_shares.append(sub["sentiment_label"].eq("neutral").sum() / n * 100)

            fig_div = go.Figure()
            fig_div.add_trace(go.Bar(
                name="Positive", y=brand_labels, x=pos_shares, orientation="h",
                marker_color="#5a8a5a",
                hovertemplate="%{y}: +%{x:.1f}%<extra>Positive</extra>",
            ))
            fig_div.add_trace(go.Bar(
                name="Neutral", y=brand_labels, x=neu_shares, orientation="h",
                marker_color="#5a5a55",
                hovertemplate="%{y}: %{x:.1f}%<extra>Neutral</extra>",
            ))
            fig_div.add_trace(go.Bar(
                name="Negative", y=brand_labels, x=neg_shares, orientation="h",
                marker_color="#b8463f",
                hovertemplate="%{y}: %{x:.1f}%<extra>Negative</extra>",
            ))
            fig_div.add_vline(x=0, line_color="#e6e3da", line_width=1)
            fig_div.update_layout(barmode="relative", height=220, **PLOTLY_DARK)
            fig_div.update_layout(title=dict(text="Sentiment Share-of-Voice by Brand", x=0.01))
            fig_div.update_xaxes(title_text="← Negative  |  Positive →", ticksuffix="%")
            fig_div.update_yaxes(title_text="")
            st.plotly_chart(fig_div, use_container_width=True)

            col_pos, col_neg = st.columns(2)
            with col_pos:
                st.markdown('<div class="cc-section-eyebrow" style="color:#5a8a5a;">Most Positive</div>', unsafe_allow_html=True)
                for _, row in df_sent.nlargest(5, "sentiment_score").iterrows():
                    title = _esc(str(row['title'])[:120])
                    url = row.get("source_url", "")
                    title_link = f'<a href="{url}" target="_blank" style="color:#1a1a1a;text-decoration:none;border-bottom:1px solid #c9a96e;">{title}</a>' if url else f'<span style="color:#1a1a1a;">{title}</span>'
                    st.markdown(f"""
<div style="border-left:3px solid #5a8a5a;padding:0.6rem 0.75rem;margin-bottom:0.5rem;background:#fafaf7;">
  <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
    <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;font-weight:700;color:#5a8a5a;">{row['sentiment_score']:+.2f}</span>
    <span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;color:#c9a96e;font-style:italic;">{_esc(row['competitor'])}</span>
  </div>
  <div style="font-size:0.88rem;font-weight:600;line-height:1.35;margin-bottom:0.2rem;">{title_link}</div>
  <div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:#888;text-transform:uppercase;letter-spacing:0.08em;">{_esc(row['source_name'])}</div>
</div>
""", unsafe_allow_html=True)
            with col_neg:
                st.markdown('<div class="cc-section-eyebrow" style="color:#b8463f;">Most Negative</div>', unsafe_allow_html=True)
                for _, row in df_sent.nsmallest(5, "sentiment_score").iterrows():
                    title = _esc(str(row['title'])[:120])
                    url = row.get("source_url", "")
                    title_link = f'<a href="{url}" target="_blank" style="color:#1a1a1a;text-decoration:none;border-bottom:1px solid #b8463f;">{title}</a>' if url else f'<span style="color:#1a1a1a;">{title}</span>'
                    st.markdown(f"""
<div style="border-left:3px solid #b8463f;padding:0.6rem 0.75rem;margin-bottom:0.5rem;background:#fafaf7;">
  <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
    <span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;font-weight:700;color:#b8463f;">{row['sentiment_score']:+.2f}</span>
    <span style="font-family:JetBrains Mono,monospace;font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;color:#c9a96e;font-style:italic;">{_esc(row['competitor'])}</span>
  </div>
  <div style="font-size:0.88rem;font-weight:600;line-height:1.35;margin-bottom:0.2rem;">{title_link}</div>
  <div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:#888;text-transform:uppercase;letter-spacing:0.08em;">{_esc(row['source_name'])}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="cc-divider-heavy"/>', unsafe_allow_html=True)

    # Video Pulse
    yt_conn = get_connection()
    df_yt = pd.read_sql_query(
        """
        SELECT competitor, title, source_url, engagement_metrics, published_at
        FROM items
        WHERE source_type = 'video_content'
          AND engagement_metrics IS NOT NULL
          AND published_at >= datetime('now', ?)
        """,
        yt_conn,
        params=(f"-{days_back} days",),
    )
    yt_conn.close()
    if selected_brands:
        df_yt = df_yt[df_yt["competitor"].isin(selected_brands)]

    if not df_yt.empty:
        def _yt_metric(row, key):
            try:
                m = _json.loads(row) if row else {}
            except Exception:
                m = {}
            v = m.get(key, 0)
            return int(v) if isinstance(v, (int, float)) else 0

        df_yt["views"] = df_yt["engagement_metrics"].apply(lambda r: _yt_metric(r, "views"))
        df_yt["likes"] = df_yt["engagement_metrics"].apply(lambda r: _yt_metric(r, "likes"))
        df_yt["comments"] = df_yt["engagement_metrics"].apply(lambda r: _yt_metric(r, "comments"))

        st.markdown('<div class="cc-section-eyebrow">Video Pulse</div>', unsafe_allow_html=True)
        st.markdown('<div class="cc-section-title" style="font-size:1.4rem;">YouTube Engagement</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Videos", f"{len(df_yt):,}")
        k2.metric("Total Views", f"{df_yt['views'].sum():,}")
        k3.metric("Total Likes", f"{df_yt['likes'].sum():,}")
        k4.metric("Total Comments", f"{df_yt['comments'].sum():,}")

        yt_brand_eng = df_yt.groupby("competitor")[["views", "likes", "comments"]].sum().reset_index()
        brands_yt = yt_brand_eng["competitor"].tolist()
        fig_yt_eng = go.Figure()
        fig_yt_eng.add_trace(go.Bar(
            name="Likes", x=brands_yt, y=yt_brand_eng["likes"],
            marker_color="#a87b5c", yaxis="y1",
        ))
        fig_yt_eng.add_trace(go.Bar(
            name="Comments", x=brands_yt, y=yt_brand_eng["comments"],
            marker_color="#7a5a3a", yaxis="y1",
        ))
        fig_yt_eng.add_trace(go.Scatter(
            name="Views", x=brands_yt, y=yt_brand_eng["views"],
            mode="lines+markers", line=dict(color="#c9a96e", width=2),
            marker=dict(size=8), yaxis="y2",
        ))
        fig_yt_eng.update_layout(height=300, barmode="group", **PLOTLY_DARK)
        fig_yt_eng.update_layout(
            title=dict(text="Engagement by Brand", x=0.01),
            yaxis=dict(title="Likes / Comments"),
            yaxis2=dict(title="Views", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig_yt_eng, use_container_width=True)

        top_video = df_yt.sort_values("views", ascending=False).head(1)
        if not top_video.empty:
            tv = top_video.iloc[0]
            tv_title = _esc(str(tv.get("title", ""))[:120])
            tv_url = str(tv.get("source_url", ""))
            tv_link = f'<a href="{tv_url}" target="_blank" style="color:#1a1a1a;text-decoration:none;border-bottom:1px solid #c9a96e;">{tv_title}</a>' if tv_url else tv_title
            st.markdown(
                f"""
<div style="margin-top:0.6rem;padding:0.7rem 0.9rem;background:#fafaf7;border-left:3px solid #c9a96e;">
  <div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;letter-spacing:0.14em;text-transform:uppercase;color:#888;margin-bottom:0.3rem;">Top video · {_esc(tv['competitor'])}</div>
  <div style="font-size:0.9rem;font-weight:600;line-height:1.3;margin-bottom:0.25rem;">{tv_link}</div>
  <div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#888;">▶ {tv['views']:,} views &nbsp; ♥ {tv['likes']:,} &nbsp; 💬 {tv['comments']:,}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)

    # X / Twitter
    st.markdown('<div class="cc-section-eyebrow">Social Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title" style="font-size:1.4rem;">Posts on X</div>', unsafe_allow_html=True)
    df_x = load_x_posts(days=days_back)
    if selected_brands:
        df_x = df_x[df_x["competitor"].isin(selected_brands)]

    if df_x.empty:
        with st.expander("No X posts yet — expand to learn more"):
            st.info("Run the pipeline with an XAI_API_KEY set to fetch live X posts via Grok.")
    else:
        def _parse_engagement(excerpt: str):
            m = _re.match(r"\[Likes:\s*(\d+),\s*Retweets:\s*(\d+)\]\s*(.*)", str(excerpt), _re.DOTALL)
            if m:
                return int(m.group(1)), int(m.group(2)), m.group(3).strip()
            return 0, 0, str(excerpt).strip()

        def _strip_excerpt_prefix(excerpt: str) -> str:
            return _re.sub(r"^\[[^\]]*\]\s*", "", str(excerpt or "")).strip()

        rows = df_x.to_dict("records")
        for r in rows:
            metrics_json = r.get("engagement_metrics")
            metrics = None
            if metrics_json:
                try:
                    metrics = _json.loads(metrics_json)
                except Exception:
                    metrics = None
            if metrics:
                r["likes"] = int(metrics.get("likes", 0))
                r["retweets"] = int(metrics.get("retweets", 0))
                r["post_text"] = _strip_excerpt_prefix(r["excerpt"])
            else:
                r["likes"], r["retweets"], r["post_text"] = _parse_engagement(r["excerpt"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("X Posts", len(rows))
        m2.metric("Total Likes", f"{sum(r['likes'] for r in rows):,}")
        m3.metric("Total Retweets", f"{sum(r['retweets'] for r in rows):,}")
        m4.metric("Brands", df_x["competitor"].nunique())

        brand_eng = pd.DataFrame(rows).groupby("competitor")[["likes", "retweets"]].sum().reset_index()
        fig_eng = px.bar(
            brand_eng.melt(id_vars="competitor", value_vars=["likes", "retweets"],
                           var_name="Metric", value_name="Count"),
            x="competitor", y="Count", color="Metric", barmode="group",
            labels={"competitor": "Brand"},
            color_discrete_map={"likes": "#c9a96e", "retweets": "#a87b5c"},
        )
        fig_eng.update_layout(height=300, **PLOTLY_DARK)
        fig_eng.update_layout(title=dict(text="Engagement by Brand", x=0.01))
        st.plotly_chart(fig_eng, use_container_width=True)

        brand_filter = st.multiselect(
            "Filter posts by brand",
            options=sorted(df_x["competitor"].unique()),
            default=sorted(df_x["competitor"].unique()),
            key="x_brand_filter",
        )
        filtered_rows = [r for r in rows if r["competitor"] in brand_filter]

        for r in filtered_rows:
            author = r["source_name"].replace("X - ", "")
            date_str = r["published_at"][:10] if r["published_at"] else ""
            sent_label = r.get("sentiment_label") or "neutral"
            sent_score = r.get("sentiment_score")
            sent_color = {"positive": "#5a8a5a", "very_positive": "#3a6a3a", "negative": "#b8463f", "very_negative": "#8a2020"}.get(sent_label, "#888")
            sent_str = f"{sent_score:+.2f}" if sent_score is not None else "—"
            post_text = _esc(r["post_text"] or "")
            brand_color = {"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"}.get(r["competitor"], "#1a1a1a")
            view_link = f'<a href="{r["source_url"]}" target="_blank" style="color:#888;font-size:0.7rem;font-family:JetBrains Mono,monospace;text-transform:uppercase;letter-spacing:0.1em;">View on X →</a>' if r.get("source_url") else ""
            st.markdown(f"""
<div style="border:1px solid #e6e3da;border-left:3px solid {brand_color};padding:0.85rem 1rem;margin-bottom:0.6rem;background:#ffffff;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
    <div style="display:flex;align-items:center;gap:0.6rem;">
      <span style="background:{brand_color};color:#fff;font-family:JetBrains Mono,monospace;font-size:0.6rem;letter-spacing:0.14em;text-transform:uppercase;padding:2px 8px;">{_esc(r['competitor'])}</span>
      <span style="font-weight:600;font-size:0.85rem;color:#1a1a1a;">@{_esc(author)}</span>
    </div>
    <div style="display:flex;align-items:center;gap:1rem;">
      <span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:{sent_color};font-weight:600;">{sent_label.upper()} {sent_str}</span>
      <span style="font-family:JetBrains Mono,monospace;font-size:0.68rem;color:#888;">{date_str}</span>
    </div>
  </div>
  <div style="font-size:0.9rem;color:#1a1a1a;line-height:1.5;margin-bottom:0.5rem;">{post_text}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>{view_link}</div>
    <div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#888;">♥ {r['likes']} &nbsp; ↻ {r['retweets']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not df_events.empty:
        df_social = df_events[df_events["source_type"] == "social_media"].copy()
        if not df_social.empty:
            st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)
            st.markdown('<div class="cc-section-eyebrow">Social Sources</div>', unsafe_allow_html=True)
            col_sc, col_ss = st.columns(2)
            with col_sc:
                source_counts = df_social.groupby("source_name").size().reset_index(name="Articles")
                fig_sc = px.bar(
                    source_counts.sort_values("Articles", ascending=False),
                    x="source_name", y="Articles",
                )
                fig_sc.update_traces(marker_color="#c9a96e")
                fig_sc.update_layout(height=300, **PLOTLY_DARK)
                fig_sc.update_layout(title=dict(text="Articles by Social Source", x=0.01))
                st.plotly_chart(fig_sc, use_container_width=True)
            with col_ss:
                source_sent = df_social.groupby("source_name")["sentiment_score"].mean().reset_index()
                source_sent.columns = ["Source", "Avg Sentiment"]
                fig_ss = px.bar(
                    source_sent.sort_values("Avg Sentiment", ascending=False),
                    x="Source", y="Avg Sentiment", text="Avg Sentiment",
                )
                fig_ss.update_traces(marker_color="#a87b5c",
                                     texttemplate="%{text:+.2f}", textposition="outside",
                                     textfont=dict(color="#e8e6df"))
                fig_ss.add_hline(y=0, line_dash="dash", line_color="#3a3a3a")
                fig_ss.update_layout(height=300, **PLOTLY_DARK)
                fig_ss.update_layout(title=dict(text="Avg Sentiment by Social Source", x=0.01))
                st.plotly_chart(fig_ss, use_container_width=True)


# ─── Tab 4b: Competitor Comparison ──────────────────────────
with tab_compare:
    st.markdown('<div class="cc-section-eyebrow">Head-to-Head</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Competitor Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Chanel vs Dior vs Gucci — event mix, activity trends, and key metrics side-by-side.</div>', unsafe_allow_html=True)

    if df_events.empty:
        st.markdown('<div style="color:#888;font-size:0.9rem;">No data available. Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        df_cmp = df_events[df_events["event_type"].notna()].copy()
        df_cmp["event_label"] = df_cmp["event_type"].str.replace("_", " ").str.title()

        # ── Row 1: KPI comparison strip ──
        st.markdown('<div class="cc-section-eyebrow">Key Metrics</div>', unsafe_allow_html=True)
        kpi_cols = st.columns(3)
        for i, brand in enumerate(BRANDS):
            sub = df_events[df_events["competitor"] == brand]
            sub_evt = df_cmp[df_cmp["competitor"] == brand]
            n_art = sub["item_id"].nunique()
            n_evt = len(sub_evt)
            avg_imp = sub_evt["impact_score"].mean()
            avg_rel = sub_evt["relevance_score"].mean()
            avg_snt = sub["sentiment_score"].mean() if "sentiment_score" in sub.columns else float("nan")
            with kpi_cols[i]:
                brand_color = BRAND_COLORS[brand]
                st.markdown(f"""
<div style="border-top:3px solid {brand_color};padding:0.9rem 1rem;background:#fff;border:1px solid #e6e3da;border-top:3px solid {brand_color};">
  <div style="font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:500;color:#1a1a1a;margin-bottom:0.6rem;">{brand}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
    <div><div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.16em;text-transform:uppercase;color:#888;">Articles</div><div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;color:#1a1a1a;">{n_art}</div></div>
    <div><div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.16em;text-transform:uppercase;color:#888;">Events</div><div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;color:#1a1a1a;">{n_evt}</div></div>
    <div><div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.16em;text-transform:uppercase;color:#888;">Avg Impact</div><div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;color:#1a1a1a;">{"N/A" if pd.isna(avg_imp) else f"{avg_imp:.1f}"}</div></div>
    <div><div style="font-family:'JetBrains Mono',monospace;font-size:0.58rem;letter-spacing:0.16em;text-transform:uppercase;color:#888;">Sentiment</div><div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;color:{"#5a8a5a" if not pd.isna(avg_snt) and avg_snt > 0.1 else "#b8463f" if not pd.isna(avg_snt) and avg_snt < -0.1 else "#888"};">{"N/A" if pd.isna(avg_snt) else f"{avg_snt:+.2f}"}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)

        # ── Row 2: Event-type distribution — grouped bar ──
        st.markdown('<div class="cc-section-eyebrow">Event Mix</div>', unsafe_allow_html=True)
        event_counts = (
            df_cmp.groupby(["event_label", "competitor"])["item_id"]
            .nunique()
            .reset_index(name="count")
        )
        fig_grouped = px.bar(
            event_counts, x="event_label", y="count",
            color="competitor", barmode="group",
            labels={"event_label": "Event Type", "count": "Articles", "competitor": "Brand"},
            color_discrete_map=CHART_BRANDS,
        )
        fig_grouped.update_layout(height=380, **PLOTLY_DARK)
        fig_grouped.update_layout(title=dict(text="Articles per Event Type — All Brands", x=0.01))
        fig_grouped.update_xaxes(tickangle=-30)
        st.plotly_chart(fig_grouped, use_container_width=True)

        # ── Row 3: Normalised share — what % of each brand's events are each type? ──
        totals = df_cmp.groupby("competitor")["item_id"].nunique().rename("total")
        share_df = event_counts.join(totals, on="competitor")
        share_df["share_pct"] = share_df["count"] / share_df["total"] * 100
        fig_share = px.bar(
            share_df, x="competitor", y="share_pct",
            color="event_label", barmode="stack",
            labels={"competitor": "Brand", "share_pct": "Share (%)", "event_label": "Event Type"},
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_share.update_layout(height=360, **PLOTLY_DARK)
        fig_share.update_layout(title=dict(text="Event-Type Mix (Normalised Share)", x=0.01))
        fig_share.update_yaxes(title_text="Share of Events (%)", ticksuffix="%")
        st.plotly_chart(fig_share, use_container_width=True)

        st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)

        # ── Row 4: Activity over time per brand, per event type ──
        st.markdown('<div class="cc-section-eyebrow">Activity Over Time</div>', unsafe_allow_html=True)
        event_type_filter = st.multiselect(
            "Filter by event type",
            options=sorted(df_cmp["event_label"].unique()),
            default=sorted(df_cmp["event_label"].unique()),
            key="compare_event_filter",
        )
        df_time = df_cmp[df_cmp["event_label"].isin(event_type_filter)].copy()
        df_time["date"] = pd.to_datetime(df_time["published_at"], errors="coerce").dt.normalize()
        df_time = df_time.dropna(subset=["date"])

        if not df_time.empty:
            daily_brand = (
                df_time.groupby(["date", "competitor"])["item_id"]
                .nunique()
                .reset_index(name="articles")
            )
            fig_time = px.line(
                daily_brand, x="date", y="articles", color="competitor",
                labels={"date": "Date", "articles": "Events", "competitor": "Brand"},
                color_discrete_map=CHART_BRANDS,
            )
            fig_time.update_layout(height=320, **PLOTLY_DARK)
            fig_time.update_layout(title=dict(text="Daily Event Volume — All Brands", x=0.01))
            fig_time.update_traces(line=dict(width=2))
            st.plotly_chart(fig_time, use_container_width=True)

        # ── Row 5: Impact × Relevance scatter per brand ──
        st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="cc-section-eyebrow">Quality Signal</div>', unsafe_allow_html=True)
        df_scatter = df_cmp[df_cmp["impact_score"].notna() & df_cmp["relevance_score"].notna()].copy()
        if not df_scatter.empty:
            fig_ir = px.scatter(
                df_scatter, x="relevance_score", y="impact_score",
                color="competitor", symbol="competitor",
                hover_data=["event_label", "title"],
                labels={"relevance_score": "Relevance", "impact_score": "Impact", "competitor": "Brand"},
                color_discrete_map=CHART_BRANDS,
                opacity=0.7,
            )
            fig_ir.update_layout(height=360, **PLOTLY_DARK)
            fig_ir.update_layout(title=dict(text="Impact vs Relevance — Every Event", x=0.01))
            fig_ir.update_traces(marker=dict(size=7, line=dict(color="#1a1a1a", width=0.5)))
            st.plotly_chart(fig_ir, use_container_width=True)
            st.markdown('<div style="font-size:0.78rem;color:#888;letter-spacing:0.04em;margin:-0.5rem 0 1rem;">Upper-right = high impact + on-topic. Each dot is one classified event.</div>', unsafe_allow_html=True)

        # ── Row 6: Brand-similarity embeddings ──
        st.markdown('<hr class="cc-divider"/>', unsafe_allow_html=True)
        st.markdown('<div class="cc-section-eyebrow">Semantic Positioning</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.82rem;color:#888;margin-bottom:0.8rem;">'
            'Weekly brand centroids derived from article embeddings. '
            'Cosine similarity shows how closely brands\' narrative spaces overlap. '
            'PCA projection reveals convergence or divergence over time.'
            '</div>',
            unsafe_allow_html=True,
        )
        df_bv = load_brand_vectors()
        if df_bv.empty:
            st.markdown('<div style="color:#888;font-size:0.9rem;">No embeddings available yet. Run the pipeline first.</div>', unsafe_allow_html=True)
        else:
            bv_brands = sorted(df_bv["brand"].unique())
            # ── Current-week similarity heatmap ──
            latest_week = df_bv["week"].max()
            latest_df = df_bv[df_bv["week"] == latest_week]
            latest_map = {r["brand"]: np.array(r["centroid"]) for _, r in latest_df.iterrows()}
            common_brands = [b for b in BRANDS if b in latest_map]
            if len(common_brands) >= 2:
                sim_matrix = np.zeros((len(common_brands), len(common_brands)))
                for i, bi in enumerate(common_brands):
                    for j, bj in enumerate(common_brands):
                        sim_matrix[i, j] = float(np.dot(latest_map[bi], latest_map[bj]))
                fig_hm = go.Figure(data=go.Heatmap(
                    z=sim_matrix,
                    x=common_brands, y=common_brands,
                    colorscale="RdBu", zmid=0,
                    text=[[f"{sim_matrix[i,j]:.3f}" for j in range(len(common_brands))]
                          for i in range(len(common_brands))],
                    texttemplate="%{text}",
                    showscale=True,
                ))
                fig_hm.update_layout(height=300, **PLOTLY_DARK)
                fig_hm.update_layout(title=dict(text=f"Brand Narrative Similarity — Week of {str(latest_week)[:10]}", x=0.01))
                st.plotly_chart(fig_hm, use_container_width=True)
                st.markdown('<div style="font-size:0.78rem;color:#888;margin:-0.5rem 0 0.5rem;">1.0 = identical narrative space. Values above 0.85 indicate converging brand positioning.</div>', unsafe_allow_html=True)

            # ── Similarity over time ──
            weeks = sorted(df_bv["week"].unique())
            if len(weeks) >= 2 and len(common_brands) >= 2:
                sim_rows = []
                for w in weeks:
                    w_df = df_bv[df_bv["week"] == w]
                    w_map = {r["brand"]: np.array(r["centroid"]) for _, r in w_df.iterrows()}
                    for i, bi in enumerate(common_brands):
                        for bj in common_brands[i+1:]:
                            if bi in w_map and bj in w_map:
                                sim = float(np.dot(w_map[bi], w_map[bj]))
                                sim_rows.append({"week": w, "pair": f"{bi} × {bj}", "similarity": sim})
                if sim_rows:
                    df_sim_ts = pd.DataFrame(sim_rows)
                    fig_sim = px.line(
                        df_sim_ts, x="week", y="similarity", color="pair",
                        labels={"week": "Week", "similarity": "Cosine Similarity", "pair": "Brand Pair"},
                        color_discrete_sequence=["#b5936c", "#5a7a4e", "#8a7a9e"],
                    )
                    fig_sim.update_layout(height=300, **PLOTLY_DARK)
                    fig_sim.update_layout(title=dict(text="Narrative Similarity Over Time", x=0.01))
                    fig_sim.update_traces(line=dict(width=2))
                    fig_sim.update_yaxes(range=[0, 1])
                    st.plotly_chart(fig_sim, use_container_width=True)

            # ── PCA 2D trajectory ──
            all_centroids = df_bv[df_bv["brand"].isin(BRANDS)].copy()
            if len(all_centroids) >= 3:
                try:
                    from sklearn.decomposition import PCA
                    matrix = np.stack(all_centroids["centroid"].tolist())
                    pca = PCA(n_components=2, random_state=42)
                    coords = pca.fit_transform(matrix)
                    all_centroids = all_centroids.copy()
                    all_centroids["PC1"] = coords[:, 0]
                    all_centroids["PC2"] = coords[:, 1]
                    all_centroids["week_str"] = all_centroids["week"].astype(str).str[:10]
                    fig_pca = px.scatter(
                        all_centroids, x="PC1", y="PC2",
                        color="brand", text="week_str",
                        labels={"PC1": f"PC1 ({pca.explained_variance_ratio_[0]:.0%})",
                                "PC2": f"PC2 ({pca.explained_variance_ratio_[1]:.0%})",
                                "brand": "Brand"},
                        color_discrete_map=CHART_BRANDS,
                    )
                    # Connect dots per brand with lines
                    for brand in all_centroids["brand"].unique():
                        bd = all_centroids[all_centroids["brand"] == brand].sort_values("week")
                        fig_pca.add_trace(go.Scatter(
                            x=bd["PC1"], y=bd["PC2"],
                            mode="lines",
                            line=dict(color=CHART_BRANDS.get(brand, "#888"), width=1, dash="dot"),
                            showlegend=False,
                            hoverinfo="skip",
                        ))
                    fig_pca.update_traces(marker=dict(size=9, line=dict(color="#1a1a1a", width=0.5)),
                                          textfont=dict(size=8, color="#888"), textposition="top center",
                                          selector=dict(mode="markers+text"))
                    fig_pca.update_layout(height=420, **PLOTLY_DARK)
                    fig_pca.update_layout(title=dict(text="Brand Narrative Trajectory (PCA)", x=0.01))
                    st.plotly_chart(fig_pca, use_container_width=True)
                    st.markdown('<div style="font-size:0.78rem;color:#888;margin:-0.5rem 0 1rem;">Each point = one week\'s brand centroid. Dotted lines show the trajectory. Proximity = narrative overlap.</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.caption(f"PCA unavailable: {e}")


# ─── Tab 5: Weekly Brief (PDF-style) ─────────────────────────
with tab_brief:
    st.markdown('<div class="cc-section-eyebrow">Editorial Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Weekly Intelligence Brief</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">A polished editorial dossier — ready to share with executives.</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 4])
    with col_a:
        if st.button("Regenerate", key="regen_brief"):
            with st.spinner("Generating brief…"):
                generate_brief()
                st.cache_data.clear()
            st.success("Brief regenerated.")
    briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True)
    file_label = files[0].name if files else "—"
    with col_c:
        st.markdown(f'<div style="font-family:JetBrains Mono;font-size:0.7rem;letter-spacing:0.14em;color:#888;text-transform:uppercase;padding-top:0.5rem;">File · {file_label}</div>', unsafe_allow_html=True)

    brief_md = load_brief()
    with col_b:
        pdf_filename = f"brief_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        pdf_bytes = _brief_to_pdf(brief_md)
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            key="download_brief_pdf",
        )
    today_long = datetime.now(timezone.utc).strftime("%d %B %Y").upper()
    brief_html = mistune.html(brief_md)

    st.markdown(f"""
<div class="cc-brief-doc">
  <div class="docline">
    <span>C&amp;C Intelligence</span>
    <span>Confidential · Internal Distribution</span>
    <span class="right">{today_long}</span>
  </div>
  {brief_html}
</div>
""", unsafe_allow_html=True)


# ─── Tab 7: Search ────────────────────────────────────────────
with tab_search:
    st.markdown('<div class="cc-section-eyebrow">Corpus Retrieval</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Semantic Search</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Find articles by meaning, not just keywords. Powered by the same embeddings used for clustering.</div>', unsafe_allow_html=True)

    query = st.text_input("Search the corpus…", placeholder='e.g. "Dior sustainability sourcing"')
    if query:
        with st.spinner("Searching…"):
            corpus = load_corpus()
        if not corpus:
            st.markdown('<div style="color:#888;font-size:0.9rem;">No embeddings found. Run the pipeline first.</div>', unsafe_allow_html=True)
        else:
            q_emb = embed_text(query)
            emb_matrix = np.stack([item["embedding"] for item in corpus])
            scores = emb_matrix @ q_emb
            top_idx = np.argsort(scores)[::-1][:10]
            st.markdown(f"**Top {len(top_idx)} results** for _{query}_")
            for rank, idx in enumerate(top_idx, 1):
                item = corpus[int(idx)]
                score = float(scores[idx])
                date_str = (item.get("published_at") or "")[:10]
                brand = item.get("competitor", "")
                title = item.get("title") or "(no title)"
                excerpt = item.get("excerpt") or ""
                url = item.get("source_url", "")
                source = item.get("source_name", "")
                st.markdown(f"""
<div style="border:1px solid #2a2a2a;border-radius:6px;padding:0.75rem 1rem;margin-bottom:0.5rem;">
<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.25rem;">
  <span style="font-weight:600;font-size:0.95rem;">{rank}. <a href="{url}" target="_blank" style="color:#c9a96e;text-decoration:none;">{title}</a></span>
  <span style="font-size:0.78rem;color:#888;">score {score:.3f}</span>
</div>
<div style="font-size:0.8rem;color:#aaa;margin-bottom:0.3rem;">{brand} · {source} · {date_str}</div>
<div style="font-size:0.85rem;color:#ccc;">{excerpt[:200]}{"…" if len(excerpt) > 200 else ""}</div>
</div>
""", unsafe_allow_html=True)
