# trends_reddit_apify.py
# Uses: themineworks/reddit-scraper
# Goal: High-evidence Reddit source for Merch Scout trend pipeline

import os
import re
import time
from typing import List, Dict, Any
from apify_client import ApifyClient

#SUBREDDITS = [
#    "funny",
#    "memes",
#    "showerthoughts",
#    "wholesomememes",
#    "AskReddit",
#    "facepalm",
#    "NotTheOnion",
#    "antiwork",
#    "gaming",
#    "parenting"
#]

SUBREDDITS = [
    "antiwork",        # Corporate burnout, office humor
    "nursing",         # Healthcare workers (highly identity-driven)
    "teachers",        # Education humor, school life
    "houseplants",     # Plant parents
    "boardgames",      # D&D, tabletop nerds
    "crochet",         # Crafters, yarn, cozy hobbies
    "TrueCrime",       # True crime junkies (massive POD niche)
    "gymmemes",        # Fitness, gym bros
    "woodworking",     # Makers, craftsmen
    "Overwatch"        # Gamers (or pick another specific game)
]

POSTS_PER_SUBREDDIT = 15  # Lowered to force diversity and prevent one sub from dominating


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
        #"this", "that", "these", "those",
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

    print(
        f"🚀 Pulling Reddit trends via themineworks/reddit-scraper "
        f"for {len(SUBREDDITS)} subreddits (one call each)..."
    )

    trends = []
    failed_subs = []
    empty_subs = []

    for idx, sub in enumerate(SUBREDDITS, 1):
        print(f"   [{idx}/{len(SUBREDDITS)}] r/{sub} ...")

        sub_input = {
            "mode": "subreddit",
            "subreddits": [sub],   # single subreddit per call
            "sortBy": "hot",
            "maxPosts": POSTS_PER_SUBREDDIT,
            "includeComments": False
        }

        try:
            run = client.actor("themineworks/reddit-scraper").call(run_input=sub_input)
            dataset = client.dataset(run["defaultDatasetId"])

            sub_items = [
                it for it in dataset.iterate_items()
                if it.get("_type") not in ("summary", "info")
            ]

            print(f"   [r/{sub}] returned {len(sub_items)} items")

            if not sub_items:
                empty_subs.append(sub)

            for item in sub_items:
                # Skip stickied/pinned moderator posts
                if item.get("is_pinned", False):
                    continue

                title = (item.get("title") or "").strip()

                if not title:
                    continue

                if not is_valid_trend(title):
                    continue

                subreddit = item.get("subreddit") or sub
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

        except Exception as e:
            print(f"   ⚠️ [r/{sub}] failed: {e}")
            failed_subs.append(sub)

        # Be polite between Apify calls — the actor rate-limits when hammered.
        # Skip the sleep after the last sub.
        if idx < len(SUBREDDITS):
            time.sleep(2)

    print(f"📊 Apify Reddit trends fetched: {len(trends)}")

    if empty_subs:
        print(f"⚠️ Subreddits that returned 0 items: {empty_subs}")
    if failed_subs:
        print(f"⚠️ Subreddits that errored out: {failed_subs}")

    if len(trends) < 30:
        print(
            "⚠️ WARNING: Apify returned fewer than 30 posts total. "
            "Some subreddits may be rate-limiting or the actor may be flaky."
        )

    return trends, {
        "empty_subs": empty_subs,
        "failed_subs": failed_subs,
    }


if __name__ == "__main__":
    # Test script directly
    results, health = get_reddit_trends_apify()
    print(f"\nCompleted standalone test: {len(results)} posts returned.")
    print(f"Health: {health}")