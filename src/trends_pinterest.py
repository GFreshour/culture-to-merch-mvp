# trends_pinterest.py
import os
import math
from typing import List, Dict, Any
from apify_client import ApifyClient

# Actor 1: Your existing trending keyword discoverer
TRENDS_ACTOR = "automation-lab/pinterest-trends-scraper"
# Actor 2: The new engagement (exact save count) scraper
SAVES_ACTOR = "thequietstack/pinterest-scraper"


def _calculate_pinterest_strength(avg_saves: float) -> int:
    """
    Maps Pinterest save counts to a 0-100 strength score.
    """
    if avg_saves <= 0:
        return 0
    # Log scale: 0 saves -> 0, ~10k saves -> ~100.
    score = min(100, (math.log1p(avg_saves) / 10.8) * 100)
    return int(round(score))


def get_pinterest_trends() -> List[Dict[str, Any]]:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("⚠️ Missing APIFY_TOKEN environment variable")
        return []

    client = ApifyClient(token)

    # --- STEP 1: Discover trending keywords ---
    print(f"🚀 Discovering Pinterest trends via {TRENDS_ACTOR}...")
    trending_keywords = []
    try:
        run = client.actor(TRENDS_ACTOR).call(run_input={
            "countries": ["US"],
            "trendTypes": ["growing"],
            "maxResultsPerCountry": 10  # Keep this small to control cost
        })
        dataset = client.dataset(run["defaultDatasetId"])
        for item in dataset.iterate_items():
            keyword = (item.get("keyword") or item.get("term") or "").strip()
            if keyword and len(keyword.split()) >= 2:  # basic filter
                trending_keywords.append(keyword)
    except Exception as e:
        print(f"⚠️ Pinterest trend discovery failed: {e}")
        return []

    if not trending_keywords:
        print("⚠️ No trending keywords found on Pinterest.")
        return []

    print(f"📊 Found {len(trending_keywords)} trending keywords. Fetching exact saves...")

    # --- STEP 2: Get exact save counts for each keyword ---
    trends = []
    for term in trending_keywords:
        try:
            run = client.actor(SAVES_ACTOR).call(run_input={
                "searchTerms": [term],
                "maxItemsPerInput": 5,  # Top 5 pins is enough to gauge strength
                "exactSaves": True,     # Ensure we get the real number
            })
            dataset = client.dataset(run["defaultDatasetId"])
            
            saves_list = []
            for pin in dataset.iterate_items():
                if pin.get("saves") is not None:
                    saves_list.append(int(pin["saves"]))
            
            # Calculate average saves from the top pins found
            avg_saves = sum(saves_list) / len(saves_list) if saves_list else 0
            strength = _calculate_pinterest_strength(avg_saves)

            trends.append({
                "title": term,
                "source": "pinterest",
                "score": strength,
                "pinterest_avg_saves": int(avg_saves),
                "has_engagement": True
            })
            print(f"   📌 {term}: avg saves {int(avg_saves)} -> strength {strength}")
            
        except Exception as e:
            print(f"   ⚠️ Failed to get saves for '{term}': {e}")
            continue

    print(f"📊 Pinterest trends fetched: {len(trends)}")
    return trends


if __name__ == "__main__":
    results = get_pinterest_trends()
    for t in results:
        print(f"  - {t['title']} (strength: {t['score']}, saves: {t['pinterest_avg_saves']})")