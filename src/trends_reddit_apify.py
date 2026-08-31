# trends_reddit_apify.py
# Uses: trudax/reddit-scraper-lite
# Goal: Drop-in Reddit source for your merch trend pipeline

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


# -----------------------------------
# SAME FILTERING YOU ALREADY USE
# -----------------------------------
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


# -----------------------------------
# MAIN FUNCTION
# -----------------------------------
def get_reddit_trends_apify():
    token = os.getenv("APIFY_TOKEN")

    if not token:
        print("⚠️ Missing APIFY_TOKEN")
        return []

    client = ApifyClient(token)

    trends = []

    try:
        print("🚀 Pulling Reddit trends from Apify...")

        # Build subreddit URLs
        start_urls = []
        for sub in SUBREDDITS:
            start_urls.append(
                {"url": f"https://www.reddit.com/r/{sub}/hot/"}
            )

        run_input = {
            "startUrls": [
                {"url": "https://www.reddit.com/r/funny/hot/"},
                {"url": "https://www.reddit.com/r/memes/hot/"},
                {"url": "https://www.reddit.com/r/showerthoughts/hot/"},
                {"url": "https://www.reddit.com/r/wholesomememes/hot/"},
                {"url": "https://www.reddit.com/r/AskReddit/hot/"},
                {"url": "https://www.reddit.com/r/facepalm/hot/"},
                {"url": "https://www.reddit.com/r/NotTheOnion/hot/"},
                {"url": "https://www.reddit.com/r/antiwork/hot/"},
                {"url": "https://www.reddit.com/r/gaming/hot/"},
                {"url": "https://www.reddit.com/r/parenting/hot/"}
            ],

            "sort": "hot",
            "skipComments": True,
            "maxComments": 0,
            "skipCommunity": True,
            "includeNSFW": False,

            "maxItems": 50,
            "maxPostCount": 8,

            "proxy": {
                "useApifyProxy": True
            }
        }

        run = client.actor("trudax/reddit-scraper-lite").call(
            run_input=run_input
        )

        dataset = client.dataset(run["defaultDatasetId"])

        for item in dataset.iterate_items():

            # Helpful if actor field names vary
            title = (
                item.get("title")
                or item.get("postTitle")
                or item.get("name")
                or ""
            ).strip()

            if not title:
                continue

            if not is_valid_trend(title):
                continue

            subreddit = (
                item.get("communityName")
                or item.get("subreddit")
                or ""
            )
            
            #subreddit = (
            #    item.get("subreddit")
            #    or item.get("communityName")
            #    or item.get("source")
            #    or ""
            #)

            score = (
                item.get("upVotes")
                or item.get("score")
                or item.get("upvotes")
                or 0
            )
            
            #score = (
            #    item.get("score")
            #    or item.get("upvotes")
            #    or 0
            #)

            print(
                f"REDDIT: {title[:60]} | "
                f"sub={subreddit} | "
                f"votes={score} | "
                f"comments={item.get('numberOfComments', 0)} | "
                f"body_chars={len(item.get('body') or '')}"
            )

            trends.append({
                "title": title,
                "subreddit": subreddit,
                "score": item.get("upVotes") or item.get("score") or 0,
                "comment_count": item.get("numberOfComments") or 0,
                "post_body": (item.get("body") or "").strip(),
                "created_at": item.get("createdAt") or "",
                "source": "reddit"
            })
            #trends.append({
            #    "title": title,
            #    "subreddit": subreddit,
            #    "score": score
            #})

        print(f"📊 Apify Reddit trends fetched: {len(trends)}")
        return trends

    except Exception as e:
        print(f"⚠️ Apify Reddit failed: {e}")
        return []