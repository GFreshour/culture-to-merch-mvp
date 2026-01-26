import feedparser

GOOGLE_TRENDS_RSS = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"

def get_daily_trends():
    feed = feedparser.parse(GOOGLE_TRENDS_RSS)

    # DEBUG: see raw feed entries
    print(f"Number of feed entries found: {len(feed.entries)}")

    trends = []
    for entry in feed.entries[:10]:
        trends.append(entry.title)

    return trends

