#!/usr/bin/env python3
"""
generate_content.py  (FREE VERSION — no paid API calls, no subscriptions)

v2 improvements:
  - Headline selection now scores multiple headlines across multiple feeds
    for market-relevance, instead of blindly taking whatever is #1 on one feed.
  - WSB "trending" tickers are now cross-checked against real price data:
    a ticker only gets tagged "Volatile" if it actually moved >=3% that day,
    otherwise it's tagged "Trending" (mentioned a lot, but not a big mover)
    or "WSB" (mentioned, move unclear/unavailable).

Pulls today's content from entirely free, keyless public sources:
  - Index moves:     Yahoo Finance via the `yfinance` library (free, no key)
  - Market news:     Free public RSS feeds (Yahoo Finance, MarketWatch, CNBC)
  - Trending stocks: Reddit's public read-only JSON endpoint for
                      r/wallstreetbets hot posts (free, no auth for this use)

No LLM API call is used — the caption is built from a template using the
real data pulled above. This keeps the entire pipeline at $0 cost forever.

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
    "https://www.marketwatch.com/rss/marketpulse",
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",  # CNBC Markets
]

MARKET_KEYWORDS = [
    "stock", "stocks", "market", "markets", "s&p", "nasdaq", "dow",
    "fed", "federal reserve", "rate", "rates", "inflation", "cpi", "gdp",
    "earnings", "shares", "index", "indices", "treasury", "yields",
    "tariff", "tariffs", "oil", "jobs report", "unemployment", "recession",
    "ipo", "merger", "acquisition", "sec", "interest rate", "bond", "bonds",
]

WSB_URL = "https://www.reddit.com/r/wallstreetbets/hot.json?limit=25"
HEADERS = {"User-Agent": "daily-market-brief-bot/1.0 (free personal project)"}

TICKER_RE = re.compile(r"\$?\b[A-Z]{2,5}\b")
COMMON_WORDS_TO_IGNORE = {
    "THE", "AND", "FOR", "YOU", "ARE", "ALL", "NOT", "BUT", "CEO", "IPO",
    "USA", "WSB", "DD", "ATH", "ATL", "YOLO", "EPS", "ETF", "IMO", "FYI",
    "SEC", "FED", "GDP", "CPI", "USD", "TLDR", "LOL", "FOMO", "EDIT", "PSA",
    "NYSE", "AKA", "ASAP", "CFO", "CTO", "COO", "IRS", "SPAC", "OTM", "ITM",
    "PSA", "IMHO", "AMA", "GG", "WTF", "NGL",
}

VOLATILE_THRESHOLD_PCT = 3.0  # a ticker moving >= this % gets tagged "Volatile"


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


def score_headline(title):
    """Higher score = more likely to be genuinely market-relevant."""
    lower = title.lower()
    return sum(1 for kw in MARKET_KEYWORDS if kw in lower)


def get_top_headline():
    """Pull entries across several feeds, score each for market relevance,
    return the highest-scoring one. Falls back to the first available
    headline if nothing scores above zero."""
    candidates = []
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "")
                if not title:
                    continue
                candidates.append((score_headline(title), title, entry.get("link", "")))
        except Exception:
            continue

    if not candidates:
        return "Markets react to overnight developments.", ""

    candidates.sort(key=lambda c: c[0], reverse=True)
    best_score, best_title, best_link = candidates[0]

    if best_score == 0:
        return candidates[0][1], candidates[0][2]

    return best_title, best_link


def get_wsb_mention_counts(limit=8):
    """Return a dict of {ticker: mention_count} from WSB hot post titles,
    most-mentioned first, up to `limit` tickers."""
    try:
        resp = requests.get(WSB_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
    except Exception:
        return {}

    ticker_counts = {}
    for post in posts:
        title = post["data"].get("title", "")
        for match in TICKER_RE.findall(title):
            t = match.replace("$", "")
            if t in COMMON_WORDS_TO_IGNORE:
                continue
            ticker_counts[t] = ticker_counts.get(t, 0) + 1

    ranked = sorted(ticker_counts.items(), key=lambda kv: kv[1], reverse=True)
    return dict(ranked[:limit])


def build_watchlist(mention_counts, max_items=4):
    """Cross-check each mentioned ticker against real price data. Only tag a
    ticker 'Volatile' if it actually moved a lot; otherwise tag by mention
    volume so the label reflects reality, not just WSB chatter."""
    watchlist = []
    for t, mentions in mention_counts.items():
        if len(watchlist) >= max_items:
            break

        pct = None
        try:
            hist = yf.Ticker(t).history(period="2d")
            if len(hist) >= 2:
                prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
                pct = (last - prev) / prev * 100
        except Exception:
            pass

        if pct is None:
            continue

        if abs(pct) >= VOLATILE_THRESHOLD_PCT:
            tag = "Volatile"
        elif mentions >= 3:
            tag = "Trending"
        else:
            tag = "WSB"

        move_note = f"moved {pct:+.1f}% today" if pct is not None else "move unconfirmed"
        watchlist.append({
            "ticker": t,
            "note": f"Mentioned {mentions}x on r/wallstreetbets today, {move_note}. "
                    f"Not a recommendation — just what's being talked about.",
            "tag": tag,
        })

    return watchlist


def build_caption(headline, index_lines, driver_headline, driver_link, watchlist):
    idx_block = "\n".join(f"• {line}" for line in index_lines)
    watch_block = "\n".join(f"• ${w['ticker']} — {w['note']}" for w in watchlist)
    if not watch_block:
        watch_block = "• No clear trending-and-confirmed movers detected this morning."

    caption = f"""📊 MORNING MARKET BRIEF — {date.today().strftime('%B %d, %Y')}

{headline}

INDICES OVERNIGHT:
{idx_block}

WHAT'S IN THE NEWS:
{driver_headline}

ON WATCH — trending AND confirmed moving today:
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
    mention_counts = get_wsb_mention_counts()
    watchlist = build_watchlist(mention_counts)

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
