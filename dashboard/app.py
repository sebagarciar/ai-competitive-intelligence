"""
Streamlit dashboard for AI Competitive Intelligence Copilot.

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
from datetime import datetime, timezone
from src.db import init_db, get_connection, get_latest_trends
from src.output.brief import generate_brief

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Chanel Competitive Intelligence",
    page_icon="🖤",
    layout="wide",
)

# Chanel-inspired CSS
st.markdown("""
<style>
/* Sidebar off-white background */
[data-testid="stSidebar"] {
    background-color: #f5f5f0;
}
/* Active tab: gold underline */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    border-bottom: 3px solid #c9a96e !important;
    color: #1a1a1a !important;
    font-weight: 600;
}
/* Tab list background */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #e0e0e0;
}
/* Custom header strip */
.chanel-header {
    background: #1a1a1a;
    color: white;
    padding: 1.1rem 1.5rem 0.9rem;
    margin-bottom: 0.75rem;
    border-bottom: 3px solid #c9a96e;
}
.chanel-header h1 {
    margin: 0 0 0.15rem;
    font-size: 1.6rem;
    letter-spacing: 0.08em;
    font-weight: 300;
}
.chanel-header p {
    margin: 0;
    font-size: 0.82rem;
    color: #c9a96e;
    letter-spacing: 0.05em;
}
/* Critical event card */
.critical-card {
    border-left: 4px solid #d9534f;
    background: #fff5f5;
    padding: 0.6rem 0.9rem;
    margin-bottom: 0.5rem;
    border-radius: 2px;
}
/* Brand badge helper (shared) */
.brand-badge {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 3px;
    font-size: 0.72rem;
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
    "positive": "😊", "very_positive": "😃",
    "negative": "😟", "very_negative": "😡",
    "neutral": "😐",
}

# ──────────────────────────────────────────────
# Data loaders
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


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────

st.sidebar.title("Filters")
selected_brands = st.sidebar.multiselect("Brands", BRANDS, default=BRANDS)
selected_types = st.sidebar.multiselect("Event Types", EVENT_TYPES, default=EVENT_TYPES)
days_back = st.sidebar.slider("Time window (days)", 7, 30, 30)

st.sidebar.divider()
if st.sidebar.button("Refresh Intelligence Data", type="primary"):
    with st.spinner("Running pipeline… this may take a few minutes"):
        try:
            from src.pipeline import run_pipeline
            run_pipeline()
            st.cache_data.clear()
            st.sidebar.success("Pipeline complete!")
        except Exception as e:
            st.sidebar.error(f"Pipeline error: {e}")

if st.sidebar.button("🔄 Reload Dashboard", help="Clear cache and reload from database"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
with st.sidebar.expander("ℹ️ How scores work"):
    st.markdown("""
**Impact** (1–5)
How significant the event is for the brand's market position.
`1` = minor mention · `5` = major market-moving event

**Relevance** (0–1)
How closely the article relates to luxury fashion competitive intelligence.
`0.8+` = highly on-topic

**Confidence** (0–1)
Classifier certainty in the event type assignment.
`0.7+` = reliable classification

**Trend Score**
`0.5 × burst_z + 0.3 × log(1+sources) + 0.2 × (impact/5)`
Higher = more unusual spike relative to the 28-day baseline.
""")

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────

st.markdown(f"""
<div class="chanel-header">
    <h1>🖤 CHANEL COMPETITIVE INTELLIGENCE</h1>
    <p>MONITORING DIOR · GUCCI &nbsp;|&nbsp; {datetime.now(timezone.utc).strftime('%d %B %Y, %H:%M UTC')}</p>
</div>
""", unsafe_allow_html=True)

init_db()

df_events = load_events(days=days_back, brands=selected_brands, event_types=selected_types)
df_trends = load_trends()

# KPI row — persistent above tabs
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Articles", len(df_events["item_id"].unique()) if not df_events.empty else 0)
col2.metric("Events Extracted", int(df_events["event_type"].notna().sum()) if not df_events.empty else 0)
col3.metric("Trends Detected", len(df_trends))
col4.metric("Critical Events", int(df_trends["is_critical"].sum()) if not df_trends.empty else 0)

if not df_events.empty and "sentiment_score" in df_events.columns:
    avg_sentiment = df_events["sentiment_score"].mean()
    emoji = "😊" if avg_sentiment > 0.2 else "😐" if avg_sentiment > -0.2 else "😟"
    col5.metric("Avg Sentiment", f"{avg_sentiment:.2f} {emoji}")
else:
    col5.metric("Avg Sentiment", "N/A")

# 6th metric: avg competitor impact (Dior + Gucci only)
df_competitors = df_events[df_events["competitor"].isin(["Dior", "Gucci"])] if not df_events.empty else pd.DataFrame()
if not df_competitors.empty and "impact_score" in df_competitors.columns:
    avg_impact = df_competitors["impact_score"].dropna().mean()
    col6.metric("Avg Competitor Impact", f"{avg_impact:.1f} / 5" if not pd.isna(avg_impact) else "N/A")
else:
    col6.metric("Avg Competitor Impact", "N/A")

st.divider()

# ── Tabs ──
tab_digest, tab_moves, tab_trends, tab_perception, tab_brief, tab_sources = st.tabs([
    "Intelligence Digest",
    "Competitor Moves",
    "Trends & Signals",
    "Brand Perception",
    "Weekly Brief",
    "Source Coverage",
])

# ─── Tab 1: Intelligence Digest ───────────────────────────────
with tab_digest:
    st.subheader("Intelligence Digest")
    st.caption("What happened this week — critical alerts, top competitor moves, and competitive positioning.")

    # A. Critical Events Alert Strip
    df_critical = df_trends[df_trends["is_critical"] == 1].sort_values("trend_score", ascending=False).head(5) if not df_trends.empty else pd.DataFrame()

    if not df_critical.empty:
        st.markdown("#### 🔴 Critical Events")
        for _, row in df_critical.iterrows():
            brand_color = BRAND_COLORS.get(row.get("competitor", ""), "#555")
            event_label = str(row.get("event_type", "")).replace("_", " ").title()
            competitor = row.get("competitor", "Unknown")
            score = row.get("trend_score", 0)
            impact = row.get("avg_impact", 0)
            count = row.get("count_7d", 0)
            st.markdown(f"""
<div class="critical-card">
<span class="brand-badge" style="background:{brand_color}">{competitor}</span>
<strong>{event_label}</strong> &nbsp;·&nbsp;
Trend score: <strong>{score:.2f}</strong> &nbsp;·&nbsp;
Avg impact: <strong>{impact:.1f}/5</strong> &nbsp;·&nbsp;
{count} articles this week
</div>
""", unsafe_allow_html=True)
    else:
        st.success("No critical events detected in this window.")

    st.divider()

    # B. This Week in Competition
    col_moves, col_trending = st.columns(2)

    with col_moves:
        st.markdown("#### Competitor Moves")
        st.caption("Top 5 events by impact (Dior & Gucci)")
        df_comp_moves = (
            df_events[df_events["competitor"].isin(["Dior", "Gucci"]) & df_events["event_type"].notna()]
            .sort_values("impact_score", ascending=False)
            .head(5)
        ) if not df_events.empty else pd.DataFrame()

        if df_comp_moves.empty:
            st.info("No competitor events found in this window.")
        else:
            for _, row in df_comp_moves.iterrows():
                brand_color = BRAND_COLORS.get(row["competitor"], "#555")
                event_label = str(row.get("event_type", "")).replace("_", " ").title()
                title = str(row.get("title", ""))[:90]
                impact = row.get("impact_score")
                source = row.get("source_name", "")
                st.markdown(f"""
<span class="brand-badge" style="background:{brand_color}">{row['competitor']}</span>
<small style="color:#666">{event_label}</small><br>
<span style="font-size:0.9rem">{title}…</span><br>
<small style="color:#999">Impact: {impact:.1f}/5 &nbsp;·&nbsp; {source}</small>
""", unsafe_allow_html=True)
                st.markdown("---")

    with col_trending:
        st.markdown("#### Trending Now")
        st.caption("Top 3 signals by trend score")
        df_top_trends = df_trends.head(3) if not df_trends.empty else pd.DataFrame()

        if df_top_trends.empty:
            st.info("No trends detected yet.")
        else:
            for _, row in df_top_trends.iterrows():
                brand_color = BRAND_COLORS.get(row.get("competitor", ""), "#555")
                event_label = str(row.get("event_type", "")).replace("_", " ").title()
                competitor = row.get("competitor", "")
                score = row.get("trend_score", 0)
                count = row.get("count_7d", 0)
                sources = row.get("unique_sources", 0)

                # Mini progress bar: score capped at 5 for display
                bar_pct = min(int(score / 5 * 100), 100)
                st.markdown(f"""
<span class="brand-badge" style="background:{brand_color}">{competitor}</span>
<small style="color:#666">{event_label}</small><br>
<div style="background:#e0e0e0;border-radius:3px;height:6px;margin:4px 0">
  <div style="background:#c9a96e;width:{bar_pct}%;height:6px;border-radius:3px"></div>
</div>
<small style="color:#999">Score: {score:.2f} &nbsp;·&nbsp; {count} articles &nbsp;·&nbsp; {sources} sources</small>
""", unsafe_allow_html=True)
                st.markdown("---")

    st.divider()

    # C. Competitive Snapshot Heatmap
    st.markdown("#### Competitive Activity Heatmap")
    st.caption("Article count by event type across brands — darker = more activity")

    if not df_events.empty and "event_type" in df_events.columns:
        df_hm = df_events[df_events["event_type"].notna()].copy()
        df_hm["event_type_label"] = df_hm["event_type"].str.replace("_", " ").str.title()

        pivot = df_hm.pivot_table(
            index="event_type_label",
            columns="competitor",
            values="item_id",
            aggfunc="nunique",
            fill_value=0,
        )
        # Ensure all 3 brands are columns even if missing
        for b in BRANDS:
            if b not in pivot.columns:
                pivot[b] = 0
        pivot = pivot[BRANDS]  # consistent column order

        z = pivot.values.tolist()
        x_labels = pivot.columns.tolist()
        y_labels = pivot.index.tolist()

        fig_hm = go.Figure(go.Heatmap(
            z=z,
            x=x_labels,
            y=y_labels,
            colorscale=[[0, "#ffffff"], [0.5, "#c9a96e"], [1, "#1a1a1a"]],
            text=[[str(v) for v in row] for row in z],
            texttemplate="%{text}",
            showscale=True,
            hovertemplate="<b>%{y}</b><br>%{x}: %{z} articles<extra></extra>",
        ))
        # Highlight Chanel column with annotation
        chanel_idx = x_labels.index("Chanel") if "Chanel" in x_labels else None
        if chanel_idx is not None:
            fig_hm.add_annotation(
                x="Chanel", y=1.08, xref="x", yref="paper",
                text="◀ US", showarrow=False,
                font=dict(color="#c9a96e", size=11),
            )
        fig_hm.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="",
            yaxis_title="",
            font=dict(size=12),
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("Run the pipeline to populate the competitive heatmap.")

# ─── Tab 2: Competitor Moves ──────────────────────────────────
with tab_moves:
    st.subheader("Competitor Moves")
    if df_events.empty:
        st.info("No events found. Run the pipeline to ingest data.")
    else:
        df_sorted = df_events[df_events["event_type"].notna()].sort_values("impact_score", ascending=False).copy()

        # Build display columns including summary and business_function
        def _truncate(text, n=120):
            s = str(text) if pd.notna(text) else ""
            return s[:n] + "…" if len(s) > n else s

        df_sorted["summary_short"] = df_sorted["summary"].apply(lambda x: _truncate(x, 120))
        df_sorted["event_type_label"] = df_sorted["event_type"].str.replace("_", " ").str.title()
        df_sorted["business_function_label"] = df_sorted["business_function"].fillna("—")
        df_sorted["published_at_fmt"] = pd.to_datetime(df_sorted["published_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        df_sorted["official_flag"] = df_sorted["official_source"].map({1: "✓", 0: ""})
        df_sorted["sentiment_emoji"] = df_sorted["sentiment_label"].fillna("neutral").map(SENTIMENT_EMOJI).fillna("😐")

        display_cols = [
            "published_at_fmt", "competitor", "event_type_label", "business_function_label",
            "title", "summary_short",
            "impact_score", "relevance_score", "confidence_score",
            "sentiment_emoji", "sentiment_score",
            "source_name", "official_flag",
        ]
        df_disp = df_sorted[display_cols].rename(columns={
            "published_at_fmt": "Date",
            "competitor": "Brand",
            "event_type_label": "Event Type",
            "business_function_label": "Function",
            "title": "Title",
            "summary_short": "Summary",
            "impact_score": "Impact",
            "relevance_score": "Relevance",
            "confidence_score": "Confidence",
            "sentiment_emoji": "Sent.",
            "sentiment_score": "Sent. Score",
            "source_name": "Source",
            "official_flag": "Official",
        })

        st.dataframe(
            df_disp,
            use_container_width=True,
            height=480,
            column_config={
                "Impact": st.column_config.NumberColumn(format="%.1f", min_value=1, max_value=5),
                "Relevance": st.column_config.NumberColumn(format="%.2f"),
                "Confidence": st.column_config.NumberColumn(format="%.2f"),
                "Sent. Score": st.column_config.NumberColumn(format="%.2f", min_value=-1, max_value=1),
            },
        )

        # Score legend
        st.caption(
            "**Impact** 1–5 (1=minor, 5=major) · "
            "**Relevance** 0–1 (closeness to luxury fashion) · "
            "**Confidence** 0–1 (classifier certainty) · "
            "**Function** = business area (product / marketing / supply_chain)"
        )

        # Evidence snippets
        with st.expander("Evidence snippets"):
            for _, row in df_sorted.head(10).iterrows():
                if row.get("evidence_snippet"):
                    st.markdown(f"**{row['competitor']} · {row['event_type_label']}**")
                    st.caption(row["evidence_snippet"])
                    if row.get("source_url"):
                        st.markdown(f"[Source]({row['source_url']})")
                    st.divider()

# ─── Tab 3: Trends & Signals ─────────────────────────────────
with tab_trends:
    st.subheader("Trends & Signals")
    if df_trends.empty:
        st.info("No trends detected yet. Run the pipeline first.")
    else:
        df_t = df_trends.copy()
        df_t["event_type_label"] = df_t["event_type"].str.replace("_", " ").str.title()

        # Bar chart
        fig_bar = px.bar(
            df_t.head(15),
            x="trend_score",
            y="event_type_label",
            color="competitor",
            orientation="h",
            barmode="group",
            title="Top Trend Scores (last pipeline run)",
            labels={"trend_score": "Trend Score", "event_type_label": "Event Type", "competitor": "Brand"},
            color_discrete_map=BRAND_COLORS,
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Scatter with annotation
        fig_scatter = px.scatter(
            df_t,
            x="burst_z",
            y="avg_impact",
            size="count_7d",
            color="competitor",
            hover_data=["event_type_label", "unique_sources", "trend_score"],
            title="Burst Intensity vs Average Impact",
            labels={"burst_z": "Burst Z-Score", "avg_impact": "Avg Impact Score", "competitor": "Brand"},
            color_discrete_map=BRAND_COLORS,
        )
        fig_scatter.update_layout(height=350)
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption("Bubble size = articles in last 7 days. Upper-right quadrant = high burst + high impact — watch these closely.")

        # Table with critical badge
        df_table = df_t[["competitor", "event_type_label", "trend_score", "count_7d", "unique_sources", "avg_impact", "is_critical"]].copy()
        df_table["is_critical"] = df_table["is_critical"].apply(lambda v: "🔴 Yes" if v else "")
        st.dataframe(
            df_table.rename(columns={
                "competitor": "Brand",
                "event_type_label": "Event Type",
                "trend_score": "Score",
                "count_7d": "7d Articles",
                "unique_sources": "Sources",
                "avg_impact": "Avg Impact",
                "is_critical": "Critical",
            }),
            use_container_width=True,
        )

# ─── Tab 4: Brand Perception ──────────────────────────────────
with tab_perception:
    st.subheader("Brand Perception")
    st.caption("Public sentiment across press and social media.")

    # ── Sentiment section ──
    if df_events.empty or "sentiment_label" not in df_events.columns or df_events["sentiment_label"].isna().all():
        st.warning("Sentiment data not yet available. Run the pipeline to analyze sentiment.")
    else:
        df_sent = df_events[df_events["sentiment_label"].notna()].copy()

        if not df_sent.empty:
            col1, col2, col3, col4 = st.columns(4)
            positive_pct = df_sent["sentiment_label"].isin(["positive", "very_positive"]).sum() / len(df_sent) * 100
            negative_pct = df_sent["sentiment_label"].isin(["negative", "very_negative"]).sum() / len(df_sent) * 100
            neutral_pct = (df_sent["sentiment_label"] == "neutral").sum() / len(df_sent) * 100
            avg_sent = df_sent["sentiment_score"].mean()
            col1.metric("Positive", f"{positive_pct:.1f}%", delta="😊")
            col2.metric("Negative", f"{negative_pct:.1f}%", delta="😟")
            col3.metric("Neutral", f"{neutral_pct:.1f}%")
            col4.metric("Avg Score", f"{avg_sent:.2f}")

            col_bar, col_pie = st.columns(2)
            with col_bar:
                brand_sent = df_sent.groupby("competitor")["sentiment_score"].mean().reset_index()
                brand_sent.columns = ["Brand", "Avg Sentiment"]
                fig_brand_sent = px.bar(
                    brand_sent, x="Brand", y="Avg Sentiment", color="Brand",
                    text="Avg Sentiment", title="Avg Sentiment by Brand",
                    color_discrete_map=BRAND_COLORS,
                )
                fig_brand_sent.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig_brand_sent.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral")
                fig_brand_sent.update_layout(height=320, showlegend=False)
                st.plotly_chart(fig_brand_sent, use_container_width=True)

            with col_pie:
                sentiment_counts = df_sent["sentiment_label"].value_counts().reset_index()
                sentiment_counts.columns = ["Sentiment", "Count"]
                fig_pie = px.pie(
                    sentiment_counts, names="Sentiment", values="Count",
                    title="Sentiment Distribution",
                    color="Sentiment",
                    color_discrete_map={
                        "positive": "#90EE90", "very_positive": "#00CC44",
                        "neutral": "#D3D3D3", "negative": "#FFB6C1", "very_negative": "#FF6B6B",
                    },
                )
                fig_pie.update_layout(height=320)
                st.plotly_chart(fig_pie, use_container_width=True)

            # Most positive / negative
            col_pos, col_neg = st.columns(2)
            with col_pos:
                st.markdown("**Most Positive 😊**")
                for _, row in df_sent.nlargest(5, "sentiment_score").iterrows():
                    st.markdown(f"**{row['competitor']}** ({row['sentiment_score']:.2f})")
                    st.caption(f"{str(row['title'])[:100]}…")
                    st.caption(f"Source: {row['source_name']}")
                    st.divider()
            with col_neg:
                st.markdown("**Most Negative 😟**")
                for _, row in df_sent.nsmallest(5, "sentiment_score").iterrows():
                    st.markdown(f"**{row['competitor']}** ({row['sentiment_score']:.2f})")
                    st.caption(f"{str(row['title'])[:100]}…")
                    st.caption(f"Source: {row['source_name']}")
                    st.divider()

    st.divider()

    # ── Social posts (X/Twitter) section ──
    st.markdown("### Social Posts (X / Twitter)")
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
            title="Total Engagement by Brand",
            labels={"competitor": "Brand"},
            color_discrete_map={"likes": "#1DA1F2", "retweets": "#17BF63"},
        )
        fig_eng.update_layout(height=280)
        st.plotly_chart(fig_eng, use_container_width=True)

        brand_filter = st.multiselect(
            "Filter posts by brand",
            options=sorted(df_x["competitor"].unique()),
            default=sorted(df_x["competitor"].unique()),
            key="x_brand_filter",
        )
        filtered_rows = [r for r in rows if r["competitor"] in brand_filter]

        for r in filtered_rows:
            color = BRAND_COLORS.get(r["competitor"], "#555")
            author = r["source_name"].replace("X - ", "")
            date_str = r["published_at"][:10] if r["published_at"] else ""
            sent_emoji = SENTIMENT_EMOJI.get(r.get("sentiment_label") or "neutral", "😐")
            sent_score = r.get("sentiment_score")
            sent_str = f"{sent_emoji} {sent_score:.2f}" if sent_score is not None else sent_emoji

            with st.container(border=True):
                col_brand, col_author, col_date, col_sent = st.columns([1, 2, 1, 1])
                col_brand.markdown(
                    f'<span class="brand-badge" style="background:{color}">{r["competitor"]}</span>',
                    unsafe_allow_html=True,
                )
                col_author.markdown(f"**{author}**")
                col_date.caption(date_str)
                col_sent.caption(f"Sentiment: {sent_str}")
                st.markdown(r["post_text"] or "_No text_")
                link_col, eng_col = st.columns([3, 1])
                if r.get("source_url"):
                    link_col.markdown(f"[View on X]({r['source_url']})")
                eng_col.caption(f"♥ {r['likes']}  &nbsp;  🔁 {r['retweets']}")

    # Social sources breakdown (from sentiment data)
    if not df_events.empty:
        df_social = df_events[df_events["source_type"] == "social_media"].copy()
        if not df_social.empty:
            st.divider()
            st.markdown("### Social Source Breakdown")
            col_sc, col_ss = st.columns(2)
            with col_sc:
                source_counts = df_social.groupby("source_name").size().reset_index(name="Articles")
                fig_sc = px.bar(source_counts.sort_values("Articles", ascending=False),
                                x="Source" if "Source" in source_counts.columns else "source_name",
                                y="Articles", title="Articles by Social Source")
                fig_sc.update_layout(height=280)
                st.plotly_chart(fig_sc, use_container_width=True)
            with col_ss:
                source_sent = df_social.groupby("source_name")["sentiment_score"].mean().reset_index()
                source_sent.columns = ["Source", "Avg Sentiment"]
                fig_ss = px.bar(source_sent.sort_values("Avg Sentiment", ascending=False),
                                x="Source", y="Avg Sentiment", text="Avg Sentiment",
                                title="Avg Sentiment by Social Source")
                fig_ss.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig_ss.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_ss.update_layout(height=280)
                st.plotly_chart(fig_ss, use_container_width=True)

# ─── Tab 5: Weekly Brief ─────────────────────────────────────
with tab_brief:
    st.subheader("Weekly Intelligence Brief")
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("Regenerate Brief"):
            with st.spinner("Generating brief…"):
                generate_brief()
                st.cache_data.clear()
            st.success("Brief regenerated!")
    with col_b:
        briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
        files = sorted(briefs_dir.glob("*.md"), reverse=True)
        if files:
            st.caption(f"Showing: {files[0].name}")

    st.markdown(load_brief())

# ─── Tab 6: Source Coverage ───────────────────────────────────
with tab_sources:
    st.subheader("Source Coverage")
    if df_events.empty:
        st.info("No data available.")
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
            "Trade Press": "#4C78A8", "Social Media": "#F58518",
            "News Aggregator": "#72B7B2", "Financial Press": "#54A24B",
            "Brand Sites": "#B279A2", "YouTube": "#E45756",
        }

        col_pie, col_bar = st.columns(2)
        with col_pie:
            cat_counts = df_cov.groupby("category")["item_id"].nunique().reset_index()
            cat_counts.columns = ["Category", "Articles"]
            fig_pie = px.pie(
                cat_counts, names="Category", values="Articles",
                title="Articles by Source Category", hole=0.35,
                color="Category", color_discrete_map=CATEGORY_COLORS,
            )
            fig_pie.update_traces(textposition="outside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            brand_cat = df_cov.groupby(["category", "competitor"])["item_id"].nunique().reset_index()
            brand_cat.columns = ["Category", "Brand", "Articles"]
            fig_brand_cat = px.bar(
                brand_cat, x="Category", y="Articles", color="Brand", barmode="stack",
                title="Brand Coverage by Source Category",
                color_discrete_map=BRAND_COLORS,
            )
            fig_brand_cat.update_layout(height=350)
            st.plotly_chart(fig_brand_cat, use_container_width=True)

        official_counts = df_events.groupby(["competitor", "official_source"])["item_id"].nunique().reset_index()
        official_counts["official_source"] = official_counts["official_source"].map({1: "Official", 0: "Media"})
        official_counts.columns = ["Brand", "Source Type", "Articles"]
        fig_official = px.bar(
            official_counts, x="Brand", y="Articles", color="Source Type",
            barmode="group", title="Official vs Media Coverage by Brand",
        )
        st.plotly_chart(fig_official, use_container_width=True)

        with st.expander("Individual source breakdown"):
            source_detail = df_cov.groupby(["category", "source_name"])["item_id"].nunique().reset_index()
            source_detail.columns = ["Category", "Source", "Articles"]
            st.dataframe(
                source_detail.sort_values(["Category", "Articles"], ascending=[True, False]),
                use_container_width=True, hide_index=True,
            )
