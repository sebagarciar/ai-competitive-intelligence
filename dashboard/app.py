"""
Streamlit dashboard for AI Competitive Intelligence Copilot.

Run with:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

# Make src importable when running from project root
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
    page_title="Luxury Intel Copilot",
    page_icon="💼",
    layout="wide",
)

BRANDS = ["Chanel", "Dior", "Gucci"]
EVENT_TYPES = [
    "collection_launch", "campaign_or_collaboration", "pricing_or_exclusivity",
    "geographic_expansion", "creative_direction", "sustainability_or_sourcing",
    "celebrity_or_influencer_alignment", "reputational_issue",
]
IMPACT_COLORS = {1: "#d4edda", 2: "#c3e6cb", 3: "#fff3cd", 4: "#ffd7a8", 5: "#f8d7da"}


# ──────────────────────────────────────────────
# Data loaders (cached per session)
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
    df = pd.read_sql_query(
        "SELECT * FROM trends ORDER BY trend_score DESC", conn
    )
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
if st.sidebar.button("Run Pipeline Now", type="primary"):
    with st.spinner("Running pipeline… this may take a few minutes"):
        try:
            from src.pipeline import run_pipeline
            run_pipeline()
            st.cache_data.clear()
            st.sidebar.success("Pipeline complete!")
        except Exception as e:
            st.sidebar.error(f"Pipeline error: {e}")

if st.sidebar.button("🔄 Refresh Data", help="Clear cache and reload from database"):
    st.cache_data.clear()
    st.rerun()

# ──────────────────────────────────────────────
# Main content
# ──────────────────────────────────────────────

st.title("💼 Luxury Fashion Competitive Intelligence")
st.caption(f"Monitoring Chanel · Dior · Gucci | Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

# Ensure DB is initialized
init_db()

# Load data
df_events = load_events(days=days_back, brands=selected_brands, event_types=selected_types)
df_trends = load_trends()

# KPI row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Articles", len(df_events["item_id"].unique()) if not df_events.empty else 0)
col2.metric("Events Extracted", df_events["event_type"].notna().sum() if not df_events.empty else 0)
col3.metric("Trends Detected", len(df_trends))
col4.metric("Critical Events", int(df_trends["is_critical"].sum()) if not df_trends.empty else 0)

# New: sentiment metrics
if not df_events.empty and "sentiment_label" in df_events.columns:
    avg_sentiment = df_events["sentiment_score"].mean() if "sentiment_score" in df_events.columns else 0
    sentiment_emoji = "😊" if avg_sentiment > 0.2 else "😐" if avg_sentiment > -0.2 else "😟"
    col5.metric("Avg Sentiment", f"{avg_sentiment:.2f} {sentiment_emoji}")
else:
    col5.metric("Avg Sentiment", "N/A")

st.divider()

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Event Table", "Trend Visualization", "Sentiment Analysis", "Weekly Brief", "Source Coverage", "X Feed"])

# ─── Tab 1: Event Table ───────────────────────────────────────
with tab1:
    st.subheader("Event Feed")
    if df_events.empty:
        st.info("No events found. Run the pipeline to ingest data.")
    else:
        display_cols = [
            "published_at", "competitor", "event_type", "title",
            "impact_score", "relevance_score", "confidence_score",
            "sentiment_label", "sentiment_score",
            "source_name", "official_source",
        ]
        df_display = df_events[display_cols].copy()
        df_display["published_at"] = pd.to_datetime(df_display["published_at"], errors="coerce").dt.strftime("%Y-%m-%d")
        df_display["official_source"] = df_display["official_source"].map({1: "✓", 0: ""})
        # Add emoji for sentiment
        sentiment_emoji_map = {
            "positive": "😊", "very_positive": "😃",
            "negative": "😟", "very_negative": "😡",
            "neutral": "😐"
        }
        if "sentiment_label" in df_display.columns:
            df_display["sentiment_label"] = df_display["sentiment_label"].fillna("neutral")
            df_display["sentiment_emoji"] = df_display["sentiment_label"].map(sentiment_emoji_map).fillna("😐")
        df_display.columns = [
            "Date", "Brand", "Event Type", "Title",
            "Impact", "Relevance", "Confidence",
            "Sentiment", "Sentiment Score", "Sentiment Emoji",
            "Source", "Official",
        ]
        df_display["Event Type"] = df_display["Event Type"].str.replace("_", " ").str.title()

        st.dataframe(
            df_display,
            use_container_width=True,
            height=500,
            column_config={
                "Impact": st.column_config.NumberColumn(format="%.1f", min_value=1, max_value=5),
                "Relevance": st.column_config.NumberColumn(format="%.1f"),
                "Confidence": st.column_config.NumberColumn(format="%.2f"),
                "Sentiment Score": st.column_config.NumberColumn(format="%.2f", min_value=-1, max_value=1),
            },
        )

        # Expandable evidence viewer
        with st.expander("View event details / evidence snippets"):
            for _, row in df_events.head(10).iterrows():
                if row.get("evidence_snippet"):
                    st.markdown(f"**{row['competitor']} · {row['event_type']}**")
                    st.caption(row["evidence_snippet"])
                    if row.get("source_url"):
                        st.markdown(f"[Source]({row['source_url']})")
                    st.divider()

# ─── Tab 2: Trend Visualization ──────────────────────────────
with tab2:
    st.subheader("Trend Scores by Brand & Event Type")
    if df_trends.empty:
        st.info("No trends detected yet. Run the pipeline first.")
    else:
        df_t = df_trends.copy()
        df_t["event_type_label"] = df_t["event_type"].str.replace("_", " ").str.title()

        # Bar chart: trend score by brand
        fig_bar = px.bar(
            df_t.head(15),
            x="trend_score",
            y="event_type_label",
            color="competitor",
            orientation="h",
            barmode="group",
            title="Top Trend Scores (last pipeline run)",
            labels={"trend_score": "Trend Score", "event_type_label": "Event Type", "competitor": "Brand"},
            color_discrete_map={"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"},
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Scatter: burst_z vs avg_impact
        fig_scatter = px.scatter(
            df_t,
            x="burst_z",
            y="avg_impact",
            size="count_7d",
            color="competitor",
            hover_data=["event_type_label", "unique_sources", "trend_score"],
            title="Burst Intensity vs Average Impact",
            labels={"burst_z": "Burst Z-Score", "avg_impact": "Avg Impact Score", "competitor": "Brand"},
            color_discrete_map={"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"},
        )
        fig_scatter.update_layout(height=350)
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Table
        st.dataframe(
            df_t[["competitor", "event_type_label", "trend_score", "count_7d", "unique_sources", "avg_impact", "is_critical"]]
            .rename(columns={
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

# ─── Tab 3: Sentiment Analysis ────────────────────────────────
with tab3:
    st.subheader("Social Listening & Sentiment Analysis")
    if df_events.empty:
        st.info("No data available. Run the pipeline to ingest social media data.")
    elif "sentiment_label" not in df_events.columns or df_events["sentiment_label"].isna().all():
        st.warning("Sentiment analysis not yet performed. Run the pipeline to analyze sentiment.")
    else:
        # Filter to items with sentiment data
        df_sent = df_events[df_events["sentiment_label"].notna()].copy()

        if df_sent.empty:
            st.info("No sentiment data available yet.")
        else:
            # Sentiment overview metrics
            col1, col2, col3, col4 = st.columns(4)
            positive_pct = (df_sent["sentiment_label"].isin(["positive", "very_positive"]).sum() / len(df_sent) * 100)
            negative_pct = (df_sent["sentiment_label"].isin(["negative", "very_negative"]).sum() / len(df_sent) * 100)
            neutral_pct = (df_sent["sentiment_label"] == "neutral").sum() / len(df_sent) * 100
            avg_sent = df_sent["sentiment_score"].mean()

            col1.metric("Positive Sentiment", f"{positive_pct:.1f}%", delta="😊")
            col2.metric("Negative Sentiment", f"{negative_pct:.1f}%", delta="😟")
            col3.metric("Neutral", f"{neutral_pct:.1f}%")
            col4.metric("Avg Sentiment Score", f"{avg_sent:.2f}")

            st.divider()

            # Sentiment by brand
            st.markdown("### Sentiment by Brand")
            brand_sent = df_sent.groupby("competitor")["sentiment_score"].agg(["mean", "count"]).reset_index()
            brand_sent.columns = ["Brand", "Avg Sentiment", "Articles"]

            fig_brand_sent = px.bar(
                brand_sent,
                x="Brand",
                y="Avg Sentiment",
                color="Brand",
                text="Avg Sentiment",
                title="Average Sentiment by Brand",
                color_discrete_map={"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"},
            )
            fig_brand_sent.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_brand_sent.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral")
            fig_brand_sent.update_layout(height=350)
            st.plotly_chart(fig_brand_sent, use_container_width=True)

            # Sentiment distribution
            st.markdown("### Sentiment Distribution")
            sentiment_counts = df_sent["sentiment_label"].value_counts().reset_index()
            sentiment_counts.columns = ["Sentiment", "Count"]

            # Create color map for sentiment
            sentiment_colors = {
                "positive": "#90EE90",
                "very_positive": "#00FF00",
                "neutral": "#D3D3D3",
                "negative": "#FFB6C1",
                "very_negative": "#FF6B6B"
            }

            fig_sent_dist = px.pie(
                sentiment_counts,
                names="Sentiment",
                values="Count",
                title="Sentiment Label Distribution",
                color="Sentiment",
                color_discrete_map=sentiment_colors,
            )
            st.plotly_chart(fig_sent_dist, use_container_width=True)

            # Social media breakdown
            st.markdown("### Social Media Sources")
            social_sources = df_sent[df_sent["source_type"] == "social_media"]

            if not social_sources.empty:
                source_counts = social_sources.groupby("source_name").size().reset_index()
                source_counts.columns = ["Source", "Articles"]

                fig_social = px.bar(
                    source_counts.sort_values("Articles", ascending=False),
                    x="Source",
                    y="Articles",
                    title="Articles from Social Media Sources",
                )
                fig_social.update_layout(height=300)
                st.plotly_chart(fig_social, use_container_width=True)

                # Sentiment by social source
                source_sent = social_sources.groupby("source_name")["sentiment_score"].mean().reset_index()
                source_sent.columns = ["Source", "Avg Sentiment"]

                fig_source_sent = px.bar(
                    source_sent.sort_values("Avg Sentiment", ascending=False),
                    x="Source",
                    y="Avg Sentiment",
                    title="Average Sentiment by Social Media Source",
                    text="Avg Sentiment",
                )
                fig_source_sent.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig_source_sent.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_source_sent, use_container_width=True)
            else:
                st.info("No social media data available yet. Enable Reddit and Twitter to see social sentiment.")

            # Most positive/negative items
            st.markdown("### Most Positive & Negative Items")
            col_pos, col_neg = st.columns(2)

            with col_pos:
                st.markdown("**Most Positive** 😊")
                top_positive = df_sent.nlargest(5, "sentiment_score")[["competitor", "title", "sentiment_score", "source_name"]]
                for _, row in top_positive.iterrows():
                    st.markdown(f"**{row['competitor']}** ({row['sentiment_score']:.2f})")
                    st.caption(f"{row['title'][:100]}...")
                    st.caption(f"Source: {row['source_name']}")
                    st.divider()

            with col_neg:
                st.markdown("**Most Negative** 😟")
                top_negative = df_sent.nsmallest(5, "sentiment_score")[["competitor", "title", "sentiment_score", "source_name"]]
                for _, row in top_negative.iterrows():
                    st.markdown(f"**{row['competitor']}** ({row['sentiment_score']:.2f})")
                    st.caption(f"{row['title'][:100]}...")
                    st.caption(f"Source: {row['source_name']}")
                    st.divider()

# ─── Tab 4: Weekly Brief ─────────────────────────────────────
with tab4:
    st.subheader("Weekly Intelligence Brief")
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("Regenerate Brief"):
            with st.spinner("Generating brief…"):
                brief_md = generate_brief()
                st.cache_data.clear()
            st.success("Brief regenerated!")
    with col_b:
        briefs_dir = Path(__file__).parent.parent / "data" / "briefs"
        files = sorted(briefs_dir.glob("*.md"), reverse=True)
        if files:
            st.caption(f"Showing: {files[0].name}")

    brief_content = load_brief()
    st.markdown(brief_content)

# ─── Tab 5: Source Coverage ───────────────────────────────────
with tab5:
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
            "Trade Press": "#4C78A8",
            "Social Media": "#F58518",
            "News Aggregator": "#72B7B2",
            "Financial Press": "#54A24B",
            "Brand Sites": "#B279A2",
            "YouTube": "#E45756",
        }

        # Pie: articles by category
        cat_counts = df_cov.groupby("category")["item_id"].nunique().reset_index()
        cat_counts.columns = ["Category", "Articles"]
        fig_pie = px.pie(
            cat_counts,
            names="Category",
            values="Articles",
            title="Articles by Source Category",
            hole=0.35,
            color="Category",
            color_discrete_map=CATEGORY_COLORS,
        )
        fig_pie.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Bar: brand coverage per category
        brand_cat = df_cov.groupby(["category", "competitor"])["item_id"].nunique().reset_index()
        brand_cat.columns = ["Category", "Brand", "Articles"]
        fig_brand_cat = px.bar(
            brand_cat,
            x="Category",
            y="Articles",
            color="Brand",
            barmode="stack",
            title="Brand Coverage by Source Category",
            color_discrete_map={"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"},
        )
        fig_brand_cat.update_layout(height=350)
        st.plotly_chart(fig_brand_cat, use_container_width=True)

        # Official vs media breakdown
        official_counts = df_events.groupby(["competitor", "official_source"])["item_id"].nunique().reset_index()
        official_counts["official_source"] = official_counts["official_source"].map({1: "Official", 0: "Media"})
        official_counts.columns = ["Brand", "Source Type", "Articles"]
        fig_official = px.bar(
            official_counts,
            x="Brand",
            y="Articles",
            color="Source Type",
            barmode="group",
            title="Official vs Media Coverage by Brand",
        )
        st.plotly_chart(fig_official, use_container_width=True)

        # Detailed breakdown in expander
        with st.expander("Individual source breakdown"):
            source_detail = df_cov.groupby(["category", "source_name"])["item_id"].nunique().reset_index()
            source_detail.columns = ["Category", "Source", "Articles"]
            st.dataframe(
                source_detail.sort_values(["Category", "Articles"], ascending=[True, False]),
                use_container_width=True,
                hide_index=True,
            )

# ─── Tab 6: X Feed ────────────────────────────────────────────
with tab6:
    import re as _re

    st.subheader("X (Twitter) Feed")
    st.caption("Live posts fetched via Grok — updated each pipeline run.")

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

    df_x = load_x_posts(days=days_back)
    if selected_brands:
        df_x = df_x[df_x["competitor"].isin(selected_brands)]

    if df_x.empty:
        st.info("No X posts yet. Run the pipeline to fetch live X data via Grok.")
    else:
        # Parse likes/retweets from excerpt prefix "[Likes: N, Retweets: N] text"
        def _parse_engagement(excerpt: str):
            m = _re.match(r"\[Likes:\s*(\d+),\s*Retweets:\s*(\d+)\]\s*(.*)", str(excerpt), _re.DOTALL)
            if m:
                return int(m.group(1)), int(m.group(2)), m.group(3).strip()
            return 0, 0, str(excerpt).strip()

        rows = df_x.to_dict("records")
        for r in rows:
            r["likes"], r["retweets"], r["post_text"] = _parse_engagement(r["excerpt"])

        # Summary metrics
        total_posts = len(rows)
        total_likes = sum(r["likes"] for r in rows)
        total_rt = sum(r["retweets"] for r in rows)
        brand_counts = df_x["competitor"].value_counts()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Posts", total_posts)
        m2.metric("Total Likes", f"{total_likes:,}")
        m3.metric("Total Retweets", f"{total_rt:,}")
        m4.metric("Brands", len(brand_counts))

        st.divider()

        # Engagement bar chart per brand
        brand_eng = (
            pd.DataFrame(rows)
            .groupby("competitor")[["likes", "retweets"]]
            .sum()
            .reset_index()
        )
        fig_eng = px.bar(
            brand_eng.melt(id_vars="competitor", value_vars=["likes", "retweets"],
                           var_name="Metric", value_name="Count"),
            x="competitor", y="Count", color="Metric", barmode="group",
            title="Total Engagement by Brand",
            labels={"competitor": "Brand"},
            color_discrete_map={"likes": "#1DA1F2", "retweets": "#17BF63"},
        )
        fig_eng.update_layout(height=300)
        st.plotly_chart(fig_eng, use_container_width=True)

        st.divider()

        # Brand filter pills
        brand_filter = st.multiselect(
            "Filter by brand", options=sorted(df_x["competitor"].unique()),
            default=sorted(df_x["competitor"].unique()), key="x_brand_filter"
        )
        filtered_rows = [r for r in rows if r["competitor"] in brand_filter]

        # Post cards
        BRAND_COLORS = {"Chanel": "#1a1a1a", "Dior": "#b5936c", "Gucci": "#5a7a4e"}
        SENTIMENT_EMOJI = {
            "positive": "😊", "very_positive": "😃",
            "negative": "😟", "very_negative": "😡",
            "neutral": "😐",
        }

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
                    f'<span style="background:{color};color:white;padding:2px 8px;'
                    f'border-radius:4px;font-size:0.75rem">{r["competitor"]}</span>',
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
