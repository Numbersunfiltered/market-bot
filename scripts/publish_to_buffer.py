#!/usr/bin/env python3
"""
publish_to_buffer.py
Takes today's generated caption + hashtags + image, and creates a scheduled
Instagram post via Buffer's GraphQL API (api.buffer.com).

Buffer's API requires the image to be reachable at a public URL (it does not
accept direct file uploads). This script assumes the GitHub Actions workflow
has already committed posts/post_YYYY-MM-DD.png to the repo and pushed it, so
we can point Buffer at the jsDelivr CDN mirror of that file:

    https://cdn.jsdelivr.net/gh/<owner>/<repo>@main/posts/post_YYYY-MM-DD.png

Required env vars:
  BUFFER_API_KEY        - personal API key from https://buffer.com (Settings > API)
  BUFFER_CHANNEL_ID     - the channelId of your connected Instagram account in Buffer
  GITHUB_REPOSITORY     - auto-set by GitHub Actions as "owner/repo"
  POST_HOUR_PT / POST_MINUTE_PT - optional override for schedule time (default 06:00 PT)
"""
import os
import json
import sys
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo

BUFFER_GRAPHQL_URL = "https://api.buffer.com/graphql"


def get_due_at_utc():
    """Build today's scheduled publish time in the 5:30-6:30 AM PT window, as UTC ISO8601."""
    hour = int(os.environ.get("POST_HOUR_PT", "6"))
    minute = int(os.environ.get("POST_MINUTE_PT", "0"))
    pt = ZoneInfo("America/Los_Angeles")
    local_dt = datetime.now(pt).replace(hour=hour, minute=minute, second=0, microsecond=0)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_image_url():
    repo = os.environ["GITHUB_REPOSITORY"]  # e.g. "yourname/ig-market-bot"
    today = date.today().isoformat()
    return f"https://cdn.jsdelivr.net/gh/{repo}@main/posts/post_{today}.png"


def main():
    content_path = sys.argv[1] if len(sys.argv) > 1 else f"posts/content_{date.today().isoformat()}.json"
    with open(content_path) as f:
        data = json.load(f)

    caption = data["caption"].strip()
    hashtags = data["hashtags"].strip()
    full_text = f"{caption}\n\n{hashtags}"

    image_url = build_image_url()
    due_at = get_due_at_utc()

    api_key = os.environ["BUFFER_API_KEY"]
    channel_id = os.environ["BUFFER_CHANNEL_ID"]

    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id dueAt }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "text": full_text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": due_at,
            "assets": [{"image": {"url": image_url}}],
        }
    }

    resp = requests.post(
        BUFFER_GRAPHQL_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    print(json.dumps(result, indent=2))

    if "errors" in result or (
        "data" in result and result["data"]["createPost"].get("message")
    ):
        print("Buffer reported an error creating the post. See output above.")
        sys.exit(1)

    print(f"Scheduled successfully for {due_at} (image: {image_url})")


if __name__ == "__main__":
    main()
