# trends_reddit_apify.py
# Uses: themineworks/reddit-scraper
# Goal: High-evidence Reddit source for Merch Scout trend pipeline

import os
import re
from typing import List, Dict, Any
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

POSTS_PER_SUBREDDIT = 5  # Keeps daily pull ~50 posts to control Apify costs


# -----------------------------------
# RULE-BASED PRE-FILTER
# -----------------------------------
def is_valid_trend(title: str) -> bool:
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


# -----------------------------------
# MAIN SCRAPER FUNCTION
# -----------------------------------
def get_reddit_trends_apify() -> List[Dict[str, Any]]:
    # Uses your existing environment variable
    token = os.getenv("APIFY_TOKEN")

    if not token:
        print("⚠️ Missing APIFY_TOKEN environment variable")
        return []

    client = ApifyClient(token)

    run_input = {
        "mode": "subreddit",
        "subreddits": SUBREDDITS,
        "sortBy": "hot",
        "maxPosts": POSTS_PER_SUBREDDIT,
        "includeComments": False
    }

    print(f"🚀 Pulling Reddit trends via themineworks/reddit-scraper for {len(SUBREDDITS)} subreddits...")

    try:
        run = client.actor("themineworks/reddit-scraper").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"])

        trends = []

        for item in dataset.iterate_items():
            # Skip non-post summary/info objects returned by actor
            if item.get("_type") in ["summary", "info"]:
                continue

            # Skip stickied/pinned moderator posts
            if item.get("is_pinned", False):
                continue

            title = (item.get("title") or "").strip()

            if not title:
                continue

            if not is_valid_trend(title):
                continue

            subreddit = item.get("subreddit") or ""
            score = item.get("score") or 0
            upvote_ratio = item.get("upvote_ratio") or 0.0
            comment_count = item.get("num_comments") or 0
            post_body = (item.get("selftext") or "").strip()
            url = item.get("permalink") or item.get("url") or ""

            # Debug printout so you can verify live evidence in logs
            print("\n========== REDDIT EVIDENCE ==========")
            print("TITLE:", title)
            print("SUBREDDIT:", subreddit)
            print("SCORE:", score)
            print("UPVOTE RATIO:", upvote_ratio)
            print("COMMENTS:", comment_count)
            print("BODY:", repr(post_body[:200]))
            print("=====================================\n")

            trends.append({
                "title": title,
                "subreddit": subreddit,
                "score": score,
                "upvote_ratio": upvote_ratio,
                "comment_count": comment_count,
                "post_body": post_body,
                "url": url,
                "source": "reddit"
            })

        print(f"📊 Apify Reddit trends fetched: {len(trends)}")
        return trends

    except Exception as e:
        print(f"⚠️ Apify Reddit failed: {e}")
        return []


if __name__ == "__main__":
    # Test script directly
    results = get_reddit_trends_apify()
    print(f"\nCompleted standalone test: {len(results)} posts returned.")