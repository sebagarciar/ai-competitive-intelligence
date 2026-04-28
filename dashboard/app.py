"""
Streamlit dashboard for AI Competitive Intelligence Copilot.

Editorial-intelligence redesign — Bloomberg Terminal × Vogue Business.
All data logic preserved verbatim from the original; only layout, styling,
and component choices have changed.

Run with:
    streamlit run dashboard/app.py
"""
import re as _re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mistune
from datetime import datetime, timezone
from src.db import init_db, get_connection, get_latest_trends
from src.output.brief import generate_brief

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
    grid-template-columns: repeat(6, 1fr);
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
               sentiment_label, sentiment_score
        FROM items
        WHERE source_name LIKE 'X - @%'
          AND published_at >= datetime('now', ?)
        ORDER BY published_at DESC
    """, conn, params=(f"-{days} days",))
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_brief() -> str:
    briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
    files = sorted(briefs_dir.glob("*.md"), reverse=True)
    if files:
        return files[0].read_text(encoding="utf-8")
    return "_No brief generated yet. Run the pipeline first._"


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
    st.rerun()

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
total_articles = len(df_events["item_id"].unique()) if not df_events.empty else 0
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
    <div class="cc-kpi"><div class="label">Articles</div><div class="value">{total_articles:,}</div><div class="delta">{days_back}D WINDOW</div></div>
    <div class="cc-kpi"><div class="label">Events</div><div class="value">{events_extracted:,}</div><div class="delta">EXTRACTED</div></div>
    <div class="cc-kpi gold"><div class="label">Trends</div><div class="value">{trends_count}</div><div class="delta">DETECTED</div></div>
    <div class="cc-kpi alert"><div class="label">Critical</div><div class="value">{critical_count}</div><div class="delta">FLAGGED</div></div>
    <div class="cc-kpi"><div class="label">Sentiment</div><div class="value">{avg_sentiment_str}</div><div class="delta">AVG SCORE</div></div>
    <div class="cc-kpi gold"><div class="label">Comp. Impact</div><div class="value">{avg_impact_str}</div><div class="delta">DIOR + GUCCI</div></div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──
tab_digest, tab_trends, tab_perception, tab_brief, tab_sources, tab_moves = st.tabs([
    "Digest",
    "Trends",
    "Perception",
    "Weekly Brief",
    "Source Coverage",
    "Event Feed",
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
                sources = row.get("unique_sources", 0)
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

        df_table = df_t[["competitor", "event_type_label", "trend_score", "count_7d",
                         "unique_sources", "avg_impact", "is_critical"]].copy()
        df_table["is_critical"] = df_table["is_critical"].apply(lambda v: "● Critical" if v else "")
        st.dataframe(
            df_table.rename(columns={
                "competitor": "Brand", "event_type_label": "Event Type",
                "trend_score": "Score", "count_7d": "7d Articles",
                "unique_sources": "Sources", "avg_impact": "Avg Impact",
                "is_critical": "Status",
            }),
            use_container_width=True, hide_index=True,
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

            col_pos, col_neg = st.columns(2)
            with col_pos:
                st.markdown('<div class="cc-section-eyebrow" style="color:#5a8a5a;">Most Positive</div>', unsafe_allow_html=True)
                for _, row in df_sent.nlargest(5, "sentiment_score").iterrows():
                    title = _esc(str(row['title'])[:120])
                    url = row.get("source_url", "")
                    title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
                    st.markdown(f"""
<div class="cc-feed-item" style="grid-template-columns:60px 1fr; padding:0.85rem 0;">
  <div class="cc-feed-meta"><div class="date" style="color:#5a8a5a;">{row['sentiment_score']:+.2f}</div></div>
  <div class="cc-feed-body">
    <span class="brand">{_esc(row['competitor'])}</span>
    <h3 style="font-size:1rem !important;">{title_html}</h3>
    <div class="source-line">{_esc(row['source_name'])}</div>
  </div>
</div>
""", unsafe_allow_html=True)
            with col_neg:
                st.markdown('<div class="cc-section-eyebrow" style="color:#b8463f;">Most Negative</div>', unsafe_allow_html=True)
                for _, row in df_sent.nsmallest(5, "sentiment_score").iterrows():
                    title = _esc(str(row['title'])[:120])
                    url = row.get("source_url", "")
                    title_html = f'<a href="{url}" target="_blank">{title}</a>' if url else title
                    st.markdown(f"""
<div class="cc-feed-item" style="grid-template-columns:60px 1fr; padding:0.85rem 0;">
  <div class="cc-feed-meta"><div class="date" style="color:#b8463f;">{row['sentiment_score']:+.2f}</div></div>
  <div class="cc-feed-body">
    <span class="brand">{_esc(row['competitor'])}</span>
    <h3 style="font-size:1rem !important;">{title_html}</h3>
    <div class="source-line">{_esc(row['source_name'])}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="cc-divider-heavy"/>', unsafe_allow_html=True)

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

        rows = df_x.to_dict("records")
        for r in rows:
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
            sent_emoji = SENTIMENT_EMOJI.get(r.get("sentiment_label") or "neutral", "—")
            sent_score = r.get("sentiment_score")
            sent_str = f"{sent_emoji} {sent_score:+.2f}" if sent_score is not None else sent_emoji
            with st.container(border=True):
                col_brand, col_author, col_date, col_sent = st.columns([1, 2, 1, 1])
                col_brand.markdown(f'<span class="brand-badge" style="background:#1a1a1a;">{r["competitor"]}</span>', unsafe_allow_html=True)
                col_author.markdown(f"**{author}**")
                col_date.caption(date_str)
                col_sent.caption(f"Sentiment: {sent_str}")
                st.markdown(r["post_text"] or "_No text_")
                link_col, eng_col = st.columns([3, 1])
                if r.get("source_url"):
                    link_col.markdown(f"[View on X]({r['source_url']})")
                eng_col.caption(f"♥ {r['likes']}  &nbsp;  ↻ {r['retweets']}")

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


# ─── Tab 6: Source Coverage ──────────────────────────────────
with tab_sources:
    st.markdown('<div class="cc-section-eyebrow">Provenance</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-title">Source Coverage</div>', unsafe_allow_html=True)
    st.markdown('<div class="cc-section-dek">Where the intelligence comes from — by category, brand, and individual outlet.</div>', unsafe_allow_html=True)

    if df_events.empty:
        st.markdown('<div style="color:#888;font-size:0.9rem;">No data available.</div>', unsafe_allow_html=True)
    else:
        def _source_category(name: str) -> str:
            n = str(name)
            if any(n.startswith(p) for p in ("Bluesky -", "Reddit -", "X - ")):
                return "Social Media"
            if "Official" in n or n in ("Chanel Official", "Dior Official", "Gucci Official"):
                return "Brand Sites"
            if n == "GDELT":
                return "News Aggregator"
            if n in ("Bloomberg Markets",):
                return "Financial Press"
            if n.startswith("YouTube"):
                return "YouTube"
            return "Trade Press"

        df_cov = df_events.copy()
        df_cov["category"] = df_cov["source_name"].apply(_source_category)

        CATEGORY_COLORS = {
            "Trade Press": "#c9a96e", "Social Media": "#a87b5c",
            "News Aggregator": "#7a8a5a", "Financial Press": "#5a8a8a",
            "Brand Sites": "#8a5a8a", "YouTube": "#b8463f",
        }

        col_pie, col_bar = st.columns(2)
        with col_pie:
            cat_counts = df_cov.groupby("category")["item_id"].nunique().reset_index()
            cat_counts.columns = ["Category", "Articles"]
            fig_pie = px.pie(
                cat_counts, names="Category", values="Articles", hole=0.5,
                color="Category", color_discrete_map=CATEGORY_COLORS,
            )
            fig_pie.update_traces(textposition="outside",
                                  texttemplate="%{label}<br>%{percent:.0%}",
                                  textfont=dict(color="#e8e6df"),
                                  marker=dict(line=dict(color="#1a1a1a", width=2)))
            fig_pie.update_layout(height=380, **PLOTLY_DARK)
            fig_pie.update_layout(
                title=dict(text="By Source Category", x=0.01),
                margin=dict(l=80, r=80, t=50, b=50),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            brand_cat = df_cov.groupby(["category", "competitor"])["item_id"].nunique().reset_index()
            brand_cat.columns = ["Category", "Brand", "Articles"]
            fig_brand_cat = px.bar(
                brand_cat, x="Category", y="Articles", color="Brand", barmode="stack",
                color_discrete_map=CHART_BRANDS,
            )
            fig_brand_cat.update_layout(height=380, **PLOTLY_DARK)
            fig_brand_cat.update_layout(title=dict(text="Brand Coverage by Category", x=0.01))
            st.plotly_chart(fig_brand_cat, use_container_width=True)

        official_counts = df_events.groupby(["competitor", "official_source"])["item_id"].nunique().reset_index()
        official_counts["official_source"] = official_counts["official_source"].map({1: "Official", 0: "Media"})
        official_counts.columns = ["Brand", "Source Type", "Articles"]
        fig_official = px.bar(
            official_counts, x="Brand", y="Articles", color="Source Type", barmode="group",
            color_discrete_map={"Official": "#c9a96e", "Media": "#5a5a55"},
        )
        fig_official.update_layout(height=340, **PLOTLY_DARK)
        fig_official.update_layout(title=dict(text="Official vs Media Coverage", x=0.01))
        st.plotly_chart(fig_official, use_container_width=True)

        with st.expander("Individual source breakdown"):
            source_detail = df_cov.groupby(["category", "source_name"])["item_id"].nunique().reset_index()
            source_detail.columns = ["Category", "Source", "Articles"]
            st.dataframe(
                source_detail.sort_values(["Category", "Articles"], ascending=[True, False]),
                use_container_width=True, hide_index=True,
            )
