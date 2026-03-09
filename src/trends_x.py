# trends_x.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_x_trends(max_items=50):
    """
    Scrape trending hashtags from X (Twitter) and return
    a list of trend dicts compatible with your pipeline.
    Each trend will have at least 'title' and 'source'.
    """
    url = "https://twitter.com/i/trends"  # public trending page placeholder
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Failed to fetch X trends: {e}")
        return []

    resp = requests.get(url, headers=headers)
    print(resp.text[:1000])  # first 1000 characters of the page
    
    # parse the HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # ⚠️ X HTML changes often; this is a generic selector
    hashtags = []
    for tag in soup.find_all("span"):
        text = tag.get_text(strip=True)
        if text.startswith("#") and len(hashtags) < max_items:
            hashtags.append({
                "title": text,
                "subreddit": "x_hashtag",   # keep the same key as Reddit trends
                "source": "X",
                "timestamp": datetime.now().isoformat()
            })

    print(f"✅ Found {len(hashtags)} X hashtag trends")
    return hashtags