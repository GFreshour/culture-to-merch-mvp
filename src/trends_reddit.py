import requests
from tier0_product_gate import run_productability_gate
import time

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
#HEADERS = {"User-Agent": "culture-to-merch-mvp/0.1"}


import re

def is_valid_trend(title: str) -> bool:
    """
    Strong deterministic filter to remove titles that
    will almost never become sellable POD text.
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
    # Reject titles that look like full narratives
    if "," in t and word_count > 10:
        return False

    return True


def fetch_subreddit_hot(subreddit, limit=25, max_retries=3):
    HEADERS = {
        "User-Agent": "python:CultureToMerchTrendScout:1.0 (by /u/gary_freshour)",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

    for attempt in range(1, max_retries+1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            if response.status_code == 429:
                print(f" Reddit rate limit hit (attempt {attempt}/{max_retries})")
                time.sleep(2 * attempt)  # exponential backoff
                continue

            if response.status_code != 200:
                print(f" ⚠️ Reddit error {response.status_code} (attempt {attempt}/{max_retries})")
                time.sleep(2 * attempt)
                continue

            data = response.json()
            return data.get("data", {}).get("children", [])

        except requests.RequestException as e:
            print(f" ⚠️ Reddit fetch failed attempt {attempt}/{max_retries}: {e}")
            time.sleep(2 * attempt)

    print(f" ⚠️ Reddit fetch ultimately failed for r/{subreddit}")
    return []


def get_reddit_trends(client):
    trends = []

    for subreddit in SUBREDDITS:
        time.sleep(1.5)
        posts = fetch_subreddit_hot(subreddit)

        for post in posts[:POST_LIMIT]:
            post_data = post.get("data", {})
            title = post_data.get("title", "").strip()

            if not title:
                continue

            # ---- Stage A: deterministic cleaning ----
            if not is_valid_trend(title):
                continue

            trend = {
                "title": title,
                "subreddit": subreddit,
                "score": post_data.get("score", 0)
            }

            trends.append(trend)
    
    trends.sort(
        key=lambda t: (t.get("productability") or {}).get("productability_score", 0),
        reverse=True
    )

    return trends
