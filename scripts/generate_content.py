#!/usr/bin/env python3
"""
generate_content.py  (FREE VERSION — no paid API calls, no subscriptions)

Pulls today's content from entirely free, keyless public sources:
  - Index moves:     Yahoo Finance via the `yfinance` library (free, no key)
  - Market news:     Free public RSS feeds (Yahoo Finance, MarketWatch)
  - Trending stocks: Reddit's public read-only JSON endpoint for
                      r/wallstreetbets hot posts (free, no auth for this use)

No LLM API call is used — the caption is built from a template using the
real data pulled above. This keeps the entire pipeline at $0 cost forever.

Trade-off vs. an LLM-written version: captions are simpler/more mechanical
rather than freshly "written." If you later want more natural prose, you
could drop in a provider with a genuinely free tier (e.g. Google Gemini's
free API tier) — entirely optional, not required for this to work.

Writes posts/content_YYYY-MM-DD.json in the same schema generate_image.py expects.
"""
import os
import re
import json
import random
from datetime import date

import requests
import feedparser
import yfinance as yf

INDICES = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^DJI": "Dow"}

NEWS_FEEDS = [
    "https://finance.yahoo.com/news/rssindex",
    "https://www.marketwatch.com/rss/topstories",
]

WSB_URL = "https://www.reddit.com/r/wallstreetbets/hot.json?limit=25"
HEADERS = {"User-Agent": "daily-market-brief-bot/1.0 (free personal project)"}

TICKER_RE = re.compile(r"\$?\b[A-Z]{2,5}\b")
COMMON_WORDS_TO_IGNORE = {
    "THE", "AND", "FOR", "YOU", "ARE", "ALL", "NOT", "BUT", "CEO", "IPO",
    "USA", "WSB", "DD", "ATH", "ATL", "YOLO", "EPS", "ETF", "IMO", "FYI",
    "SEC", "FED", "GDP", "CPI", "USD",
}


def get_index_summary():
    lines = []
    for symbol, name in INDICES.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if len(hist) < 2:
                continue
            prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
            pct = (last - prev) / prev * 100
            arrow = "+" if pct >= 0 else ""
            lines.append(f"{name}: {arrow}{pct:.2f}%")
        except Exception as e:
            lines.append(f"{name}: data unavailable ({e.__class__.__name__})")
    return lines


def get_top_headline():
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                entry = feed.entries[0]
                return entry.title, entry.get("link", "")
        except Exception:
            continue
    return "Markets react to overnight developments.", ""


def get_wsb_trending(limit=4):
    try:
        resp = requests.get(WSB_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
    except Exception:
        return []

    ticker_counts = {}
    for post in posts:
        title = post["data"].get("title", "")
        for match in TICKER_RE.findall(title):
            t = match.replace("$", "")
            if t in COMMON_WORDS_TO_IGNORE:
                continue
            ticker_counts[t] = ticker_counts.get(t, 0) + 1

    ranked = sorted(ticker_counts.items(), key=lambda kv: kv[1], reverse=True)
    return [t for t, _ in ranked[:limit]]


def build_watchlist(tickers):
    watchlist = []
    tags = ["WSB", "Trending", "Volatile", "Momentum"]
    for i, t in enumerate(tickers):
        pct_note = ""
        try:
            hist = yf.Ticker(t).history(period="2d")
            if len(hist) >= 2:
                prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
                pct = (last - prev) / prev * 100
                pct_note = f" (moved {pct:+.1f}% recently)"
        except Exception:
            pass
        watchlist.append({
            "ticker": t,
            "note": f"Actively mentioned on r/wallstreetbets today{pct_note}. "
                    f"Not a recommendation — just what's being talked about.",
            "tag": tags[i % len(tags)],
        })
    return watchlist


def build_caption(headline, index_lines, driver_headline, driver_link, watchlist):
    idx_block = "\n".join(f"• {line}" for line in index_lines)
    watch_block = "\n".join(f"• ${w['ticker']} — {w['note']}" for w in watchlist)
    if not watch_block:
        watch_block = "• No clear trending tickers detected this morning."

    caption = f"""📊 MORNING MARKET BRIEF — {date.today().strftime('%B %d, %Y')}

{headline}

INDICES OVERNIGHT:
{idx_block}

WHAT'S IN THE NEWS:
{driver_headline}

ON WATCH — trending on r/wallstreetbets right now:
{watch_block}

This is market news and public sentiment tracking, not financial advice. \
Nothing here is a buy or sell recommendation — always do your own research \
before making any investment decision.
""".strip()

    return caption


def build_hashtags():
    base = [
        "#stockmarket", "#investing", "#stocks", "#finance", "#wallstreet",
        "#trading", "#daytrading", "#stockmarketnews", "#money", "#investor",
        "#financialfreedom", "#stocktrading", "#markets", "#economy",
        "#wallstreetbets", "#investingtips", "#stockstowatch", "#nasdaq",
        "#sp500", "#dowjones",
    ]
    random.shuffle(base)
    return " ".join(base)


def generate():
    index_lines = get_index_summary()
    driver_title, driver_link = get_top_headline()
    trending_tickers = get_wsb_trending()
    watchlist = build_watchlist(trending_tickers) if trending_tickers else []

    headline = driver_title if len(driver_title) <= 60 else driver_title[:57] + "..."

    driver_text = driver_title
    if driver_link:
        driver_text += "\n(source in bio / link sticker)"

    caption = build_caption(headline, index_lines, driver_text, driver_link, watchlist)
    hashtags = build_hashtags()

    data = {
        "headline": headline,
        "index_summary": index_lines,
        "driver": driver_title,
        "watchlist": watchlist,
        "caption": caption,
        "hashtags": hashtags,
    }

    today = date.today().isoformat()
    out_path = f"posts/content_{today}.json"
    os.makedirs("posts", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {out_path}")
    return data, out_path


if __name__ == "__main__":
    generate()
