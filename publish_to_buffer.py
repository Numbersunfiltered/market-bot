name: Daily US Market Instagram Post

on:
  schedule:
    # Runs at 12:15 UTC = 5:15 AM PDT (summer) / 4:15 AM PST (winter).
    # GitHub Actions cron is UTC-only and doesn't shift for daylight saving,
    # so during PST months (winter) this will fire ~1hr earlier than in PDT
    # months. See README.md for how to adjust twice a year, or use the
    # optional DST-safe variant described there.
    - cron: "15 12 * * *"
  workflow_dispatch: {}   # lets you trigger it manually from the Actions tab to test

jobs:
  post:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install yfinance feedparser pillow requests

      - name: Generate today's market content (free public data sources)
        run: python scripts/generate_content.py

      - name: Render Instagram image
        run: python scripts/generate_image.py

      - name: Commit and push generated post
        run: |
          git config user.name "market-bot"
          git config user.email "market-bot@users.noreply.github.com"
          git add posts/
          git commit -m "Daily post $(date -u +%Y-%m-%d)" || echo "Nothing to commit"
          git push

      - name: Publish to Instagram via Buffer
        env:
          BUFFER_API_KEY: ${{ secrets.BUFFER_API_KEY }}
          BUFFER_CHANNEL_ID: ${{ secrets.BUFFER_CHANNEL_ID }}
          GITHUB_REPOSITORY: ${{ github.repository }}
        run: python scripts/publish_to_buffer.py
