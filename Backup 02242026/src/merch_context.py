from slogan_engine import generate_slogans

def generate_merch_context(trend):
    title = trend["title"]
    subreddit = trend["subreddit"]

    slogans = generate_slogans(title)

    if subreddit in ["television", "movies"]:
        vibe = "Pop Culture / TV"
        why = "Derived from a trending TV or movie discussion."
    elif subreddit in ["funny", "memes"]:
        vibe = "Humor / Meme"
        why = "Short-form humor that resonates quickly."
    elif subreddit == "showerthoughts":
        vibe = "Relatable / Thoughtful"
        why = "A thought people see and instantly relate to."
    else:
        vibe = "General"
        why = "Broad cultural relevance."

    return {
        "trend": title,
        "source": subreddit,
        "vibe": vibe,
        "why_it_works": why,
        "primary_slogan": slogans[0],
        "alt_slogans": slogans[1:],
        "design_suggestion": "Large bold text, centered, neutral background",
        "etsy_keywords": [
            "coffee mug",
            "funny mug",
            "gift idea",
            "daily mug",
            "relatable humor"
        ]
    }
