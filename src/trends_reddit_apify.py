import os
import re
from apify_client import ApifyClient

SUBREDDITS = [
    "funny",
    "memes",
    "showerthoughts",
    "wholesomememes",
    "AskReddit",
    "facepalm",
    "NotTheOnion",
    "antiwork",
    "gaming",
    "parenting"
]

POST_LIMIT = 15


def is_valid_trend(title: str):
    if not title:
        return False

    t = title.strip()
    tl = t.lower()

    word_count = len(t.split())

    if word_count < 3 or word_count > 14:
        return False

    if t.endswith("?"):
        return False

    context_phrases = [
        "this", "that", "these", "those",
        "today i", "yesterday i",
        "my boss", "my coworker",
        "look at", "watch this",
        "you won't believe",
        "happened to me",
        "tifu", "aita"
    ]

    if any(p in tl for p in context_phrases):
        return False

    blocked_phrases = [
        "reminder", "political", "ban", "mod",
        "rule", "announcement", "psa",
        "update:", "breaking", "news"
    ]

    if any(b in tl for b in blocked_phrases):
        return False

    if "http://" in tl or "https://" in tl:
        return False

    if re.search(r"[!?.]{3,}", t):
        return False

    if "," in t and word_count > 10:
        return False

    return True


def get_reddit_trends_apify():
    token = os.getenv("APIFY_TOKEN")

    if not token:
        print("⚠️ Missing APIFY_TOKEN")
        return []

    client = ApifyClient(token)

    trends = []

    try:
        run_input = {
            "subreddits": SUBREDDITS,
            "sort": "hot",
            "maxItems": len(SUBREDDITS) * POST_LIMIT
        }

        run = client.actor("trudax/reddit-hot-scraper").call(run_input=run_input)

        dataset = client.dataset(run["defaultDatasetId"])

        for item in dataset.iterate_items():
            title = item.get("title", "").strip()

            if not title:
                continue

            if not is_valid_trend(title):
                continue

            trends.append({
                "title": title,
                "subreddit": item.get("subreddit", ""),
                "score": item.get("score", 0)
            })

    except Exception as e:
        print(f"⚠️ Apify Reddit failed: {e}")
        return []

    print(f"📊 Apify Reddit trends fetched: {len(trends)}")
    return trends