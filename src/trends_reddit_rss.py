# trends_reddit_rss.py

import feedparser
import time
import re

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


def is_valid_trend(title: str) -> bool:
    """
    Same deterministic filter from your Reddit scraper
    """

    if not title:
        return False

    t = title.strip()
    tl = t.lower()

    # ---- Length checks ----
    word_count = len(t.split())
    if word_count < 3 or word_count > 14:
        return False

    # ---- Reject questions ----
    if t.endswith("?"):
        return False

    # ---- Reject obvious context-dependent phrases ----
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

    # ---- Reject meta / admin / news style ----
    blocked_phrases = [
        "reminder", "political", "ban", "mod",
        "rule", "announcement", "psa",
        "update:", "breaking", "news"
    ]

    if any(b in tl for b in blocked_phrases):
        return False

    # ---- Reject URLs ----
    if "http://" in tl or "https://" in tl:
        return False

    # ---- Reject titles with excessive punctuation ----
    if re.search(r"[!?.]{3,}", t):
        return False

    # ---- Prefer phrase-like structure ----
    if "," in t and word_count > 10:
        return False

    return True


def fetch_subreddit_rss(subreddit, max_retries=3):
    """
    Fetch subreddit via RSS instead of JSON scraping
    """
    url = f"https://www.reddit.com/r/{subreddit}/.rss"

    for attempt in range(1, max_retries + 1):
        try:
            feed = feedparser.parse(url)

            if not feed.entries:
                print(f"⚠️ Empty RSS for r/{subreddit} (attempt {attempt})")
                time.sleep(2 * attempt)
                continue

            return feed.entries

        except Exception as e:
            print(f"⚠️ RSS fetch failed for r/{subreddit} (attempt {attempt}): {e}")
            time.sleep(2 * attempt)

    print(f"⚠️ RSS ultimately failed for r/{subreddit}")
    return []


def get_reddit_trends_rss(client=None):
    """
    Drop-in replacement for get_reddit_trends()
    Returns same structure: [{title, subreddit, score}]
    """

    trends = []

    for subreddit in SUBREDDITS:
        time.sleep(1.5)  # keep your polite pacing

        entries = fetch_subreddit_rss(subreddit)

        for entry in entries[:POST_LIMIT]:
            title = entry.get("title", "").strip()

            if not title:
                continue

            # ---- SAME FILTER ----
            if not is_valid_trend(title):
                continue

            trend = {
                "title": title,
                "subreddit": subreddit,
                "score": 0  # RSS doesn't give score — your pipeline doesn't rely on it anyway
            }

            trends.append(trend)

    return trends