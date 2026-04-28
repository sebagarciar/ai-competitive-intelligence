# Social Listening Setup Guide

This guide will help you set up the new social listening capabilities for your AI Competitive Intelligence Copilot.

## Overview

The system now includes:
- **Reddit monitoring** - Consumer discussions from fashion subreddits
- **Twitter/X scraping** - Brand mentions and influencer posts (optional, fragile)
- **Sentiment analysis** - Local AI model analyzes positive/negative/neutral sentiment
- **Enhanced dashboard** - New sentiment analysis tab with visualizations

## What's New?

### 1. Free Social Listening Sources
- **Reddit (PRAW)**: Official API, very generous free tier
  - Monitors r/luxury, r/fashion, r/handbags, r/Chanel, r/Dior, r/Gucci, etc.
  - Tracks upvotes, comments, engagement metrics
  - Detects brand mentions in posts and comments

- **Twitter/X (ntscraper)**: Unofficial scraping (disabled by default)
  - Tracks hashtags (#Chanel, #Dior, #Gucci)
  - Monitors fashion influencer accounts
  - WARNING: May break if Twitter changes their site

### 2. Sentiment Analysis
- Uses `cardiffnlp/twitter-roberta-base-sentiment-latest` model
- Runs locally (no API costs)
- Analyzes every article/post/tweet for sentiment
- Scores range from -1 (very negative) to +1 (very positive)
- Labels: very_positive, positive, neutral, negative, very_negative

### 3. Dashboard Enhancements
- New "Sentiment Analysis" tab with:
  - Sentiment overview metrics
  - Sentiment by brand charts
  - Sentiment distribution
  - Social media source breakdown
  - Most positive/negative items
- Sentiment columns added to Event Table
- Sentiment emoji indicators (😊😐😟)

## Setup Instructions

### Step 1: Install New Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `praw==7.7.1` - Reddit API client
- `ntscraper==0.4.0` - Twitter scraper (optional)

### Step 2: Set Up Reddit API (RECOMMENDED)

Reddit has a generous free API - **strongly recommended** for social listening!

1. **Create a Reddit account** (if you don't have one)
   - Go to https://www.reddit.com

2. **Create a Reddit App**
   - Visit https://www.reddit.com/prefs/apps
   - Scroll down and click "Create App" or "Create Another App"
   - Fill in:
     - **name**: `luxury-brand-intelligence` (or any name)
     - **App type**: Select "script"
     - **description**: (optional)
     - **about url**: (optional)
     - **redirect uri**: `http://localhost:8080`
   - Click "Create app"

3. **Get your credentials**
   - After creating, you'll see your app details
   - **CLIENT_ID**: The string under "personal use script" (e.g., `abc123def456`)
   - **CLIENT_SECRET**: The "secret" field (e.g., `xyz789uvw456`)

4. **Update your `.env` file**
   ```bash
   REDDIT_CLIENT_ID=abc123def456
   REDDIT_CLIENT_SECRET=xyz789uvw456
   REDDIT_USER_AGENT=luxury-brand-intelligence:v1.0
   ```

**Rate Limits**: 60 requests/minute - very generous for this use case!

### Step 3: Enable Twitter Scraping (OPTIONAL)

⚠️ **WARNING**: Twitter scraping is fragile and may break without notice. Only enable if you need real-time Twitter data.

**Option A: Keep it disabled (recommended)**
```bash
# In .env file:
TWITTER_ENABLED=false
```

**Option B: Enable Twitter scraping**
```bash
# In .env file:
TWITTER_ENABLED=true
```

No API key needed, but the scraper may break if Twitter changes their website structure.

**Better alternative**: Consider Twitter API (paid) for production use.

### Step 4: Update Database Schema

The database needs new columns for sentiment data. Run:

```bash
python -m src.db
```

This will add:
- `sentiment_label` - positive/negative/neutral
- `sentiment_score` - numerical score (-1 to +1)
- `sentiment_confidence` - model confidence (0-1)

### Step 5: Run the Pipeline

Run the full pipeline to ingest social data and analyze sentiment:

```bash
python -m src.pipeline
```

The pipeline will now:
1. Fetch articles from GDELT, RSS, brand sites, YouTube (existing)
2. **NEW**: Fetch posts from Reddit
3. **NEW**: Fetch tweets from Twitter (if enabled)
4. Translate and embed all content
5. **NEW**: Analyze sentiment for all items
6. Extract events and detect trends
7. Generate intelligence brief

### Step 6: Launch the Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard now has:
- **Event Table** - Now includes sentiment columns
- **Trend Visualization** - Same as before
- **Sentiment Analysis** (NEW) - Comprehensive sentiment insights
- **Weekly Brief** - Same as before
- **Source Coverage** - Same as before

## What the System Now Tracks

### Reddit Monitoring
- **Subreddits**:
  - r/luxury, r/luxuryfashion
  - r/fashion, r/femalefashionadvice, r/malefashionadvice
  - r/handbags, r/designerbags
  - r/Chanel, r/Dior, r/Gucci

- **Engagement Metrics**:
  - Upvotes (score)
  - Number of comments
  - Upvote ratio
  - Post recency

- **What it finds**:
  - Consumer discussions about brands
  - Product reviews and opinions
  - Brand comparisons
  - Shopping advice

### Twitter Monitoring (if enabled)
- **Hashtags**: #Chanel, #ChanelFashion, #Dior, #DiorFashion, #Gucci, #GucciFashion
- **Influencer Accounts**: @voguemagazine, @CFDA, fashion influencers
- **Brand Official Accounts**: @CHANEL, @Dior, @gucci

- **Engagement Metrics**:
  - Likes
  - Retweets
  - Replies
  - Quotes
  - Influencer flag

### Sentiment Analysis
- **Applied to**: All articles, Reddit posts, tweets, YouTube videos
- **Model**: RoBERTa fine-tuned on Twitter sentiment (works well for all short-form content)
- **Output**:
  - Label: positive, negative, neutral (+ very_positive, very_negative)
  - Score: -1.0 to +1.0
  - Confidence: 0.0 to 1.0

## Troubleshooting

### Reddit API Issues

**Error: "Authentication failed"**
- Check that `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are correct
- Make sure there are no extra spaces or quotes
- Verify you created a "script" type app

**Error: "Rate limit exceeded"**
- Reddit allows 60 requests/minute
- The system respects this limit automatically
- If you hit it, wait 1 minute and try again

**No Reddit data appearing**
- Check that `.env` has the Reddit credentials
- Run `python -m src.pipeline` to ingest data
- Check console logs for "[Reddit]" messages

### Twitter Scraping Issues

**Error: "ntscraper not installed"**
```bash
pip install ntscraper==0.4.0
```

**No tweets appearing**
- Check that `TWITTER_ENABLED=true` in `.env`
- Twitter scraping is fragile - it may be broken
- Check console for "[Twitter]" error messages
- Consider disabling Twitter if it's not working

**Error: "Scraping failed"**
- Twitter changed their website structure
- This is expected with unofficial scrapers
- Disable Twitter: `TWITTER_ENABLED=false`
- Consider Twitter API (paid) for reliable access

### Sentiment Analysis Issues

**Error: "Model not found"**
- First run downloads the model (~500MB)
- Requires internet connection
- Check disk space

**Sentiment analysis is slow**
- First run downloads the model
- After that, it's fast (local inference)
- Batch processing is efficient

**All sentiments show "neutral"**
- Check that you ran the pipeline after updating
- Run: `python -m src.pipeline --skip-ingest` to reprocess existing data
- Check database: `SELECT sentiment_label FROM items LIMIT 10`

### Dashboard Issues

**Sentiment tab shows "No data available"**
- Run the pipeline first: `python -m src.pipeline`
- Make sure sentiment analysis step completed
- Check database schema was updated

**Sentiment columns show empty/N/A**
- Database needs migration
- Run: `python -m src.db`
- Then run pipeline: `python -m src.pipeline --skip-ingest`

## Performance & Costs

### API Quotas (Free Tier)
- **Reddit**: 60 requests/min - sufficient for this use case
- **Twitter**: No API quota (unofficial scraping) but fragile
- **YouTube**: 10,000 units/day (existing)

### Data Volume Expectations
Per pipeline run, you can expect:
- **Reddit**: 50-200 posts (depending on activity)
- **Twitter**: 50-150 tweets (if enabled)
- **Traditional sources**: 100-300 articles (existing)
- **Total sentiment analyses**: 200-650 items

### Processing Time
- Ingestion: 2-5 minutes
- Sentiment analysis: 1-3 minutes (first run downloads model)
- Full pipeline: 5-10 minutes

### Storage
- Sentiment model: ~500MB (one-time download)
- Database growth: ~1-2MB per pipeline run

## Best Practices

1. **Reddit is your best friend**
   - Most reliable free social listening source
   - Real consumer sentiment and discussions
   - Official API with generous limits

2. **Twitter is optional**
   - Only enable if you need it
   - Be prepared for it to break
   - Consider paid Twitter API for production

3. **Run pipeline regularly**
   - Daily runs capture fresh social discussions
   - Reddit/Twitter move fast (3-7 day lookback)
   - Weekly runs are sufficient for traditional sources

4. **Monitor sentiment trends**
   - Look for sudden drops in sentiment
   - Compare sentiment across brands
   - Social media sentiment is early warning signal

5. **Filter by source type**
   - Official sources vs social media
   - Different sentiment patterns
   - Social media shows raw consumer opinion

## What You Can Now Answer

With social listening enabled, you can answer:
- "What are consumers saying about Chanel on Reddit?"
- "Is sentiment positive or negative for Dior's new campaign?"
- "Which brand has the most positive social media buzz?"
- "Are there any emerging issues or complaints?"
- "How do influencers talk about Gucci vs competitors?"
- "What's the sentiment breakdown for each brand?"

## Next Steps

1. **Set up Reddit API** (strongly recommended)
2. **Run the pipeline** to collect social data
3. **Explore the dashboard** sentiment analysis tab
4. **Optionally enable Twitter** if needed
5. **Schedule regular pipeline runs** (daily or weekly)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review console logs for error messages
3. Verify API credentials in `.env` file
4. Check that all dependencies are installed

## Summary

You now have a comprehensive social listening system that:
✅ Monitors Reddit for consumer discussions (FREE)
✅ Optionally tracks Twitter mentions (FREE but fragile)
✅ Analyzes sentiment using local AI (FREE)
✅ Visualizes sentiment trends in dashboard
✅ Tracks engagement metrics (upvotes, comments, likes)
✅ Identifies influencer content
✅ Compares sentiment across brands

All of this using FREE sources and local AI models - no paid APIs required!
