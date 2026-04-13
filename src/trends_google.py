import feedparser
import re

GOOGLE_TRENDS_RSS = "https://trends.google.com/trending/rss?geo=US"


def is_valid_google_trend(title: str) -> bool:
    """
    Filters out low-quality or non-merchable Google trends
    """
    t = title.lower()

    # Skip very short
    if len(t.split()) < 2:
        return False

    # Skip question-style searches
    if t.startswith(("what is", "when is", "how to", "who is")):
        return False

    # Skip likely proper-name-only trends (basic heuristic)
    words = title.split()
    if len(words) == 2 and all(w[0].isupper() for w in words if w):
        return False

    return True


def get_daily_trends():
    """
    Returns structured Google Trends data for pipeline use
    """
    feed = feedparser.parse(GOOGLE_TRENDS_RSS)

    trends = []

    for entry in feed.entries[:15]:
        raw_title = entry.title.strip()

        # Light cleaning (preserve meaning)
        cleaned_title = re.sub(r"\s+", " ", raw_title)

        if not is_valid_google_trend(cleaned_title):
            continue

        trends.append({
            "title": cleaned_title,
            "source": "google_trends",
            "score": 0
        })

    return trends


def google_trend_signal(title, google_trends_today):
    """
    Checks if a given trend aligns with Google Trends
    """
    if not google_trends_today:
        return {
            "status": "Unavailable",
            "note": "Google Trends feed empty or unavailable today"
        }

    title_lc = title.lower()

    for gt in google_trends_today:
        gt_title = gt["title"].lower() if isinstance(gt, dict) else str(gt).lower()

        if gt_title in title_lc or title_lc in gt_title:
            return {
                "status": "Trending on Google",
                "note": f"Related to Google trend: {gt_title}"
            }

    return {
        "status": "Not trending",
        "note": "No strong Google Trends signal today"
    }