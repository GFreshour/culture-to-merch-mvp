import feedparser
import time
import re

# -------------------------
# CONFIG
# -------------------------

SUBSTACK_FEEDS = [
    "https://www.trendhunter.com/rss",
    "https://thegeneralist.substack.com/feed"
    #"https://feedly.com/i/discover/sources/search/feed/substack"  # optional aggregator
]

MAX_POSTS_PER_FEED = 10


# -------------------------
# CLEANING
# -------------------------

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<.*?>", "", text)  # remove HTML
    text = text.strip()

    return text


def is_valid_signal(title):
    """
    Slightly looser than Reddit filter because Substack is higher quality.
    """
    if not title:
        return False

    word_count = len(title.split())

    if word_count < 3 or word_count > 18:
        return False

    if "http" in title.lower():
        return False

    return True


# -------------------------
# AI CONVERSION
# -------------------------

def convert_to_merch_trend(title, summary, client):
    """
    Converts article insight → merch-style phrase
    """

    prompt = f"""
You are extracting a PRINT-ON-DEMAND merch phrase from a cultural article.

ARTICLE TITLE:
{title}

SUMMARY:
{summary}

Return STRICT JSON:

{{
  "trend_phrase": "",
  "angle": "",
  "target_demo": "",
  "confidence": 0
}}

RULES:
- trend_phrase must be SHORT (3–8 words)
- It must feel like something people would wear
- Avoid generic news phrasing
- Lean into identity, humor, or emotion
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        import json
        data = json.loads(content)

        return data

    except Exception as e:
        print(f"⚠️ Substack AI conversion failed: {e}")
        return None


# -------------------------
# MAIN FETCHER
# -------------------------

def get_substack_trends(client):
    trends = []

    for feed_url in SUBSTACK_FEEDS:
        print(f"📡 Fetching Substack feed: {feed_url}")

        feed = feedparser.parse(feed_url)

        entries = feed.entries[:MAX_POSTS_PER_FEED]

        for entry in entries:
            title = clean_text(entry.get("title", ""))
            summary = clean_text(
                entry.get("summary", "") or entry.get("description", "")
            )

            if not is_valid_signal(title):
                continue

            # ---- AI Conversion ----
            ai_data = convert_to_merch_trend(title, summary, client)

            if not ai_data:
                continue

            trend_phrase = ai_data.get("trend_phrase", "").strip()

            # 🔥 NEW FILTER
            if len(trend_phrase.split()) < 3:
                continue

            if trend_phrase.lower() in ["life", "success", "happiness"]:
                continue

            if not trend_phrase:
                continue

            trend = {
                "title": trend_phrase,   # IMPORTANT: downstream expects "title"
                "source": "substack",
                "original_title": title,
                "angle": ai_data.get("angle"),
                "target_demo": ai_data.get("target_demo"),
                "confidence": ai_data.get("confidence", 0)
            }

            trends.append(trend)

            time.sleep(0.8)  # rate control

    return trends