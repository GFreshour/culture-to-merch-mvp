from trends_reddit import get_reddit_trends
from trends_tiktok import get_tiktok_trends
from openai import OpenAI


def test_scrapers():

    print("Testing Reddit scraper...")

    client = OpenAI()

    reddit = get_reddit_trends(client)

    if not isinstance(reddit, list):
        raise RuntimeError("Reddit scraper did not return list")

    if reddit:
        r = reddit[0]

        if "title" not in r:
            raise RuntimeError("Reddit trend missing title")

        if "subreddit" not in r:
            raise RuntimeError("Reddit trend missing subreddit")

    print("Testing TikTok scraper...")

    tiktok = get_tiktok_trends()

    if not isinstance(tiktok, list):
        raise RuntimeError("TikTok scraper did not return list")

    print(" Scrapers OK")