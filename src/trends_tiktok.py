import requests
import re
import json

URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

HASHTAG_LIMIT = 30


def get_tiktok_trends(max_retries=3):
    trends = []

    for attempt in range(1, max_retries + 1):

        try:
            resp = requests.get(URL, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            html = resp.text

            # TikTok embeds JSON data in the page
            match = re.search(r'"hashtagName":"(.*?)"', html)

            if not match:
                print(f"⚠️ TikTok page loaded but no hashtags found (attempt {attempt}/{max_retries})")
                time.sleep(2 * attempt)
                continue

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

            print(f"Found {len(trends)} TikTok hashtag trends")

            return trends

        except requests.RequestException as e:
            print(f"⚠️ TikTok fetch failed (attempt {attempt}/{max_retries}): {e}")
            time.sleep(2 * attempt)

        except Exception as e:
            print(f"⚠️ Unexpected TikTok error (attempt {attempt}/{max_retries}): {e}")
            time.sleep(2 * attempt)

    print("⚠️ TikTok trends ultimately failed after retries")

    return []