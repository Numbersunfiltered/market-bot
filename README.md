# Daily US Market Instagram Bot — 100% Free Version

Fully automated pipeline, **$0 cost, no subscriptions, no paid API calls**:
researches overnight US market moves + trending r/wallstreetbets tickers,
writes a caption with hashtags, renders a branded image, and publishes it to
Instagram between ~5:30–6:30 AM PT every day — with zero manual steps once
set up.

**Cost breakdown (confirmed):**
| Piece | Cost |
|---|---|
| Market/index data (Yahoo Finance via `yfinance`) | Free, no key |
| News headline (public RSS feeds) | Free, no key |
| Trending tickers (Reddit's public JSON endpoint) | Free, no key |
| Image rendering (Pillow, runs in the workflow) | Free |
| Image hosting (jsDelivr CDN mirror of your public repo) | Free |
| Scheduling engine (GitHub Actions cron) | Free (public repos: unlimited minutes) |
| Posting to Instagram (Buffer free plan) | Free — 3 channels, 100 API requests/day, we use ~1/day |

No credit card is required anywhere in this setup.

**How it works:** GitHub Actions runs on a daily cron → pulls index data,
a top market headline, and trending WSB tickers from free public
sources → builds a caption from a template → renders a 1080x1080 image →
commits it to this repo → tells Buffer (free plan) to publish it to your
connected Instagram at the scheduled time.

---

## What you need to set up yourself (one-time, ~15 minutes)

I can't create accounts or enter passwords/API keys on your behalf — these
steps need to be done by you, logged into your own accounts. None of them
require payment info.

### 1. Convert your Instagram to a Professional (Business or Creator) account
Free, required for auto-publishing. Instagram app → Menu →
*For professionals* → *Account type and tools* → *Switch to professional account*.

### 2. Connect Instagram to Buffer (free plan)
- Sign up at [buffer.com](https://buffer.com) — choose the **Free** plan,
  no card needed
- **Channels → Connect a channel → Instagram**, follow the prompts (this
  requires linking a Facebook Page — Buffer walks you through it)

### 3. Get your Buffer API key and channel ID
- In Buffer: **Settings → API** → generate a Personal API Key (included free)
- Find your Instagram channel's `channelId` via Buffer's GraphQL explorer at
  developers.buffer.com, using your key:
  ```
  query { channels { id service } }
  ```

### 4. Create a GitHub repo (free) and push this code
- Create a new **public** repo (needs to be public so the free jsDelivr image
  hosting trick works — see note below) and push everything in this folder to it

### 5. Add your two secrets to the GitHub repo
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
| Secret name | Value |
|---|---|
| `BUFFER_API_KEY` | from step 3 |
| `BUFFER_CHANNEL_ID` | from step 3 |

That's it — no other keys needed. This version has no Anthropic/LLM cost.

> **Want the repo private instead?** jsDelivr's free CDN mirroring only works
> on public GitHub repos. If privacy matters more than convenience here, swap
> `publish_to_buffer.py`'s image URL for any free-tier image host with a
> direct-link upload option (e.g. Cloudinary's free tier) — ask and I'll wire
> that in.

### 6. Test it manually before trusting the schedule
Repo → **Actions** tab → **Daily US Market Instagram Post** →
**Run workflow**. Check:
- The commit to `posts/` looks right (open the generated PNG)
- Buffer shows a scheduled post on your Instagram channel

### 7. Let it run
Once the manual test works, the cron in `.github/workflows/daily-post.yml`
takes over completely.

---

## Honest limitations of the free-data approach

- **Yahoo Finance and Reddit's endpoints here are public but unofficial** —
  they can occasionally rate-limit or change format without notice. The
  script fails gracefully (skips that section) rather than crashing the
  whole post, but check in on it every so often.
- **No LLM writes the caption** — it's assembled from a template using real
  pulled data, so it reads more like a structured brief than freshly
  composed prose. If you want more natural writing later, a free-tier LLM
  API (e.g. Google Gemini's free tier) could slot in — optional, not needed
  for this to run.
- **Trending tickers come from r/wallstreetbets post titles**, filtered by a
  simple regex for likely tickers — it's a decent signal, not a perfect one.
  Obscure tickers or heavy slang days may return fewer/no hits.

## About the daylight-saving offset

GitHub Actions cron is UTC-only and doesn't shift for DST. The workflow is
set for **12:15 UTC** = 5:15 AM PDT (Mar–Nov) / 4:15 AM PST (Nov–Mar). Adjust
the cron line twice a year if you want it pinned exactly, or ask me to add
an auto-adjusting version.

## Editorial guardrails baked into the content

- Never says "buy" / "sell" / gives a recommendation
- Frames WSB-trending tickers as "what people are talking about," not signals
- Always closes with a "not financial advice, do your own research" line
- Only uses numbers actually pulled that run — nothing invented

Edit the template directly in `scripts/generate_content.py`'s
`build_caption()` function to change tone or structure.

## Files
```
scripts/generate_content.py   # free data pull + template caption (no paid API)
scripts/generate_image.py     # renders the branded PNG
scripts/publish_to_buffer.py  # schedules the Instagram post via Buffer (free plan)
.github/workflows/daily-post.yml  # the daily automation
posts/                        # generated content + images land here, dated
```
