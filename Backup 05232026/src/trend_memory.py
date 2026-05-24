import json
import os
import glob
import re
from datetime import datetime, timedelta

OUTPUT_DIR = "output"
LOOKBACK_DAYS = 5  # avoid yesterday + day before


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("#", "")
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def dedupe_trends(trends):
    """
    Remove duplicates within today's dataset
    """
    seen = set()
    result = []

    for t in trends:
        key = normalize(t["title"])

        if key in seen:
            continue

        seen.add(key)
        result.append(t)

    return result


def load_recent_titles():
    """
    Load titles from recent daily output files
    """
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    recent_titles = set()

    pattern = os.path.join(OUTPUT_DIR, "daily_merch_*.json")

    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)

        try:
            date_part = filename.replace("daily_merch_", "").replace(".json", "")
            file_date = datetime.fromisoformat(date_part)
        except Exception:
            continue

        if file_date < cutoff:
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            for item in data:
                title = item.get("title")
                if title:
                    recent_titles.add(normalize(title))

        except Exception:
            continue

    return recent_titles


def remove_recent_trends(trends):
    """
    Remove trends already sent recently
    """
    recent = load_recent_titles()

    return [
        t for t in trends
        if normalize(t["title"]) not in recent
    ]