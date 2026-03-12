import feedparser
import re

GOOGLE_TRENDS_RSS = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"

def get_daily_trends():
    """
    Returns a list of cleaned, lowercase Google daily trending search titles.
    """
    feed = feedparser.parse(GOOGLE_TRENDS_RSS)

    trends = []
    for entry in feed.entries[:10]:
        title = entry.title.lower()
        title = re.sub(r"[^a-z0-9\s]", "", title)  # strip punctuation
        trends.append(title)

    #print("Feed status:", feed.get("status", "no status"))
    #print("Feed bozo:", feed.bozo)
    #if feed.bozo:
    #    print("Feed error:", feed.bozo_exception)


    return trends

def google_trend_signal(title, google_trends_today):
    if not google_trends_today:
        return {
            "status": "Unavailable",
            "note": "Google Trends feed empty or unavailable today"
        }

    title_lc = title.lower()

    for gt in google_trends_today:
        if gt.lower() in title_lc or title_lc in gt.lower():
            return {
                "status": "Trending on Google",
                "note": f"Related to Google trend: {gt}"
            }

    return {
        "status": "Not trending",
        "note": "No strong Google Trends signal today"
    }

