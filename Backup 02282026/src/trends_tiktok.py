import requests
import re
import json

URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

HASHTAG_LIMIT = 30


def get_tiktok_trends():
    trends = []

    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        html = resp.text

        # TikTok embeds JSON data in the page
        match = re.search(r'"hashtagName":"(.*?)"', html)

        if not match:
            print("⚠️ TikTok page loaded but no hashtags found")
            return []

        tags = re.findall(r'"hashtagName":"(.*?)"', html)

        seen = set()

        for tag in tags:
            hashtag = f"#{tag}"

            if hashtag.lower() in seen:
                continue

            seen.add(hashtag.lower())

            trends.append({
                "title": hashtag,
                "subreddit": "tiktok",
                "score": 0
            })

            if len(trends) >= HASHTAG_LIMIT:
                break

        print(f"✅ Found {len(trends)} TikTok hashtag trends")

        return trends

    except Exception as e:
        print(f"⚠️ TikTok trends failed: {e}")
        return []