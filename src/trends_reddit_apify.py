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

    # Length control
    if word_count < 3 or word_count > 14:
        return False

    # Reject questions
    if t.endswith("?"):
        return False

    # Context dependent junk
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

    # Meta / admin / weak newsy titles
    blocked_phrases = [
        "reminder", "political", "ban", "mod",
        "rule", "announcement", "psa",
        "update:", "breaking", "news"
    ]

    if any(b in tl for b in blocked_phrases):
        return False

    # URLs
    if "http://" in tl or "https://" in tl:
        return False

    # Spam punctuation
    if re.search(r"[!?.]{3,}", t):
        return False

    # Weak long sentence style
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
        print("🚀 Pulling Reddit trends from Apify...")

        run_input = {
            "community_names": SUBREDDITS,
            "max_results": len(SUBREDDITS) * POST_LIMIT,
            "sort_by": "hot",
            "time_filter": "day"
        }

        run = client.actor("saswave/reddit-advanced-scraper").call(
            run_input=run_input
        )

        dataset = client.dataset(run["defaultDatasetId"])

        for item in dataset.iterate_items():

            title = (
                item.get("title")
                or item.get("post_title")
                or item.get("headline")
                or ""
            ).strip()

            if not title:
                continue

            if not is_valid_trend(title):
                continue

            subreddit = (
                item.get("subreddit")
                or item.get("community_name")
                or ""
            )

            score = (
                item.get("score")
                or item.get("upvotes")
                or 0
            )

            trends.append({
                "title": title,
                "subreddit": subreddit,
                "score": score
            })

        print(f"📊 Apify Reddit trends fetched: {len(trends)}")
        return trends

    except Exception as e:
        print(f"⚠️ Apify Reddit failed: {e}")
        return []