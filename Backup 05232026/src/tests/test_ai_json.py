#from main import enrich_top5_with_ai


def test_ai_json():

    print("Testing AI JSON response...")

    sample_trend = {
        "title": "Coffee tastes better on Mondays",
        "subreddit": "showerthoughts",
        "score": 100
    }

    result = enrich_top5_with_ai(sample_trend)

    if not isinstance(result, dict):
        raise RuntimeError("AI did not return JSON")

    if "merch_headline" not in result:
        raise RuntimeError("AI JSON missing merch_headline")

    print(" AI JSON OK")