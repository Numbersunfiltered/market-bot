#!/usr/bin/env python3
"""
generate_image.py
Renders a 1080x1080 Instagram post image from today's content JSON, using the
same dark / green-red color language as the existing morning briefing reports.

Requires: Pillow (pip install pillow)
Fonts: uses DejaVuSans bundled with Pillow's default; for a nicer look, drop
TTF files into scripts/fonts/ (Inter-Bold.ttf, Inter-Regular.ttf,
JetBrainsMono-Bold.ttf) and this script will use them automatically if present.

Usage: python generate_image.py posts/content_2026-07-14.json
Writes: posts/post_2026-07-14.png
"""
import sys
import json
import os
import textwrap
from datetime import date
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1080

BG = (10, 14, 20)
PANEL = (17, 22, 31)
BORDER = (35, 43, 56)
TEXT = (231, 236, 243)
SUB = (138, 149, 168)
GREEN = (46, 230, 166)
RED = (255, 92, 114)
AMBER = (255, 181, 71)

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


def load_font(name_bold_or_regular, size):
    candidates = {
        "bold": ["Inter-Bold.ttf", "DejaVuSans-Bold.ttf"],
        "regular": ["Inter-Regular.ttf", "DejaVuSans.ttf"],
        "mono": ["JetBrainsMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"],
    }
    for fname in candidates[name_bold_or_regular]:
        local = os.path.join(FONT_DIR, fname)
        if os.path.exists(local):
            return ImageFont.truetype(local, size)
    try:
        return ImageFont.truetype(f"DejaVuSans{'-Bold' if 'bold' in name_bold_or_regular else ''}.ttf", size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_image(data: dict, out_path: str):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = load_font("bold", 54)
    f_date = load_font("mono", 24)
    f_h2 = load_font("bold", 34)
    f_body = load_font("regular", 30)
    f_small = load_font("regular", 26)
    f_ticker = load_font("mono", 30)
    f_tag = load_font("mono", 22)

    pad = 56
    y = pad

    # Header
    d.text((pad, y), "MARKET BRIEF", font=f_title, fill=TEXT)
    y += 62
    d.text((pad, y), date.today().strftime("%A, %B %d %Y").upper(), font=f_date, fill=SUB)
    y += 50
    d.line([(pad, y), (W - pad, y)], fill=BORDER, width=2)
    y += 36

    # Headline banner
    headline = data.get("headline", "")
    lines = wrap_text(d, headline, f_h2, W - 2 * pad - 40)
    box_h = 30 + len(lines) * 42
    d.rectangle([pad, y, W - pad, y + box_h], fill=(24, 18, 22), outline=(74, 34, 48), width=2)
    ty = y + 15
    for ln in lines:
        d.text((pad + 20, ty), ln, font=f_h2, fill=(255, 255, 255))
        ty += 42
    y += box_h + 30

    # Index summary
    d.text((pad, y), "INDICES", font=load_font("mono", 22), fill=AMBER)
    y += 34
    for line in data.get("index_summary", [])[:3]:
        color = GREEN if ("+" in line or "up" in line.lower()) else RED if ("-" in line or "down" in line.lower()) else TEXT
        wrapped = wrap_text(d, line, f_body, W - 2 * pad - 20)
        for wl in wrapped:
            d.text((pad + 10, y), wl, font=f_body, fill=color)
            y += 40
        y += 4
    y += 20

    # Driver
    d.line([(pad, y), (W - pad, y)], fill=BORDER, width=2)
    y += 26
    d.text((pad, y), "WHAT'S DRIVING IT", font=load_font("mono", 22), fill=AMBER)
    y += 34
    driver_lines = wrap_text(d, data.get("driver", ""), f_small, W - 2 * pad - 20)
    for ln in driver_lines[:4]:
        d.text((pad + 10, y), ln, font=f_small, fill=(199, 206, 219))
        y += 34
    y += 26

    # Watchlist
    d.line([(pad, y), (W - pad, y)], fill=BORDER, width=2)
    y += 26
    d.text((pad, y), "ON WATCH TODAY", font=load_font("mono", 22), fill=AMBER)
    y += 40

    for item in data.get("watchlist", [])[:4]:
        ticker = item.get("ticker", "")
        note = item.get("note", "")
        tag = item.get("tag", "")

        # ticker badge
        badge_w = d.textlength(ticker, font=f_ticker) + 28
        d.rounded_rectangle([pad, y, pad + badge_w, y + 42], radius=8,
                             outline=(91, 157, 255), width=2)
        d.text((pad + 14, y + 6), ticker, font=f_ticker, fill=(91, 157, 255))

        # tag pill
        tag_x = pad + badge_w + 14
        tag_w = d.textlength(tag, font=f_tag) + 20
        d.rounded_rectangle([tag_x, y + 4, tag_x + tag_w, y + 38], radius=8, fill=(58, 44, 20))
        d.text((tag_x + 10, y + 8), tag, font=f_tag, fill=AMBER)

        y += 52
        note_lines = wrap_text(d, note, f_small, W - 2 * pad - 20)
        for nl in note_lines[:2]:
            d.text((pad + 10, y), nl, font=f_small, fill=(199, 206, 219))
            y += 32
        y += 18

    # Footer
    d.rectangle([0, H - 70, W, H], fill=PANEL)
    d.text((pad, H - 50), "Market news & education \u2014 not financial advice",
            font=load_font("mono", 20), fill=SUB)

    img.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    content_path = sys.argv[1] if len(sys.argv) > 1 else f"posts/content_{date.today().isoformat()}.json"
    with open(content_path) as f:
        data = json.load(f)
    out_path = content_path.replace("content_", "post_").replace(".json", ".png")
    build_image(data, out_path)
