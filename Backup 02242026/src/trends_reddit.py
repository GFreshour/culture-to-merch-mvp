import requests

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
HEADERS = {"User-Agent": "culture-to-merch-mvp/0.1"}


def is_valid_trend(title: str) -> bool:
    blocked_phrases = [
        "reminder",
        "political",
        "ban",
        "mod",
        "rule",
        "announcement"
    ]
    title_lower = title.lower()
    return not any(b in title_lower for b in blocked_phrases)


def fetch_subreddit_hot(subreddit: str):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    response = requests.get(url, headers=HEADERS, timeout=10)

    if response.status_code != 200:
        return []

    data = response.json()
    return data.get("data", {}).get("children", [])


def get_reddit_trends():
    trends = []

    for subreddit in SUBREDDITS:
        posts = fetch_subreddit_hot(subreddit)

        for post in posts[:POST_LIMIT]:
            post_data = post.get("data", {})
            title = post_data.get("title", "").strip()

            if not title:
                continue

            if is_valid_trend(title):
                trends.append({
                    "title": title,
                    "subreddit": subreddit,
                    "score": post_data.get("score", 0)
                })

    return trends
