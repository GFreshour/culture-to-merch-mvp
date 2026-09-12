# trends_pinterest.py
# Uses: automation-lab/pinterest-trends-scraper
# Goal: Surface Pinterest search trends as cultural signals for POD

import os
from typing import List, Dict, Any
from apify_client import ApifyClient
from source_filters import is_valid_search_trend

# Pinterest Trends scraper on Apify
# Returns trending keywords with growth scores and seasonality
PINTEREST_ACTOR = "automation-lab/pinterest-trends-scraper"

# Countries to pull trends for. Start with US only.
COUNTRIES = ["US"]

# How many trends per country
MAX_RESULTS = 25


def get_pinterest_trends() -> List[Dict[str, Any]]:
    """
    Fetch Pinterest trend keywords via Apify.

    Returns list of trend dicts matching the pipeline's expected shape:
      {
        "title": "keyword",
        "source": "pinterest",
        "score": 0,           # Pinterest doesn't give us an engagement score
        "growth": "..."       # optional metadata, if actor returns it
      }
    """
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("⚠️ Missing APIFY_TOKEN environment variable")
        return []

    client = ApifyClient(token)

    run_input = {
        "countries": COUNTRIES,
        "trendTypes": ["growing"],
        "maxResultsPerCountry": MAX_RESULTS,
    }

    print(f"🚀 Pulling Pinterest trends via {PINTEREST_ACTOR}...")

    try:
        run = client.actor(PINTEREST_ACTOR).call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"])

        trends = []

        for item in dataset.iterate_items():
            # Field name depends on actor output; be defensive.
            keyword = (
                item.get("keyword")
                or item.get("term")
                or item.get("title")
                or ""
            ).strip()

            if not keyword:
                continue

            # Shared search-source quality filter
            is_valid, reason = is_valid_search_trend(keyword)
            if not is_valid:
                print(f"   🚫 Pinterest reject: '{keyword}' ({reason})")
                continue

            trend = {
                "title": keyword,
                "source": "pinterest",
                "score": 0,  # no engagement metric from this actor
            }

            # Preserve growth metadata if present (useful later)
            if item.get("growth") or item.get("growthScore"):
                trend["pinterest_growth"] = item.get("growth") or item.get("growthScore")

            trends.append(trend)

        print(f"📊 Pinterest trends fetched: {len(trends)}")
        return trends

    except Exception as e:
        print(f"⚠️ Pinterest scraper failed: {e}")
        return []


if __name__ == "__main__":
    # Standalone test
    results = get_pinterest_trends()
    print(f"\nCompleted standalone test: {len(results)} trends returned.")
    for t in results[:5]:
        print(f"  - {t['title']} (source: {t['source']})")