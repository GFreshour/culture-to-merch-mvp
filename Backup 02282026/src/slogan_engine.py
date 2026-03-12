import re

GENERIC_FILLER = [
    "the", "and", "to", "of", "in", "for", "with", "on", "this", "that"
]

COMMON_MUG_PHRASES = [
    "It Be Like That Sometimes",
    "Well, That Escalated Quickly",
    "I Need Coffee",
    "Just One More Episode",
    "Mentally Somewhere Else",
    "I Have Questions",
    "Send Coffee",
    "This Is Fine"
]

def clean_phrase(text):
    # Remove punctuation and emojis
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

def extract_core_phrase(title):
    words = title.split()

    # Short titles are often already usable
    if len(words) <= 6:
        return clean_phrase(title)

    # Try to extract a punchy middle slice
    core = words[1:6]
    return clean_phrase(" ".join(core))

def generate_slogans(title):
    core = extract_core_phrase(title)

    slogans = []

    # Primary slogan
    slogans.append(core)

    # Variations
    slogans.append(f"{core}. Probably.")
    slogans.append(f"{core} Energy")
    slogans.append(f"Me Reading This Like: {core}")

    # Add 1–2 classic mug phrases for familiarity
    slogans.extend(COMMON_MUG_PHRASES[:2])

    # Deduplicate & keep short
    final = []
    for s in slogans:
        if s.lower() not in [f.lower() for f in final] and len(s.split()) <= 7:
            final.append(s)

    return final[:5]
