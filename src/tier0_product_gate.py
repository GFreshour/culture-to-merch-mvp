import json


def run_productability_gate(trend, client):
    """
    Tier 0 — Concept detector, not slogan detector.

    Evaluates whether a trend contains a REAL merch concept, even if the
    title itself would need rephrasing. Passes evidence context so the
    model can distinguish "thin title with strong signal" from
    "thin title with no signal."

    Deterministic: temperature=0.0 so the same trend always gets the
    same verdict. If pass rate changes between runs, it's a real change.
    """

    title = (trend.get("title") or "").strip()
    source = (trend.get("source") or "unknown").lower()

    # ---- Build an evidence summary for context ----
    evidence = trend.get("source_evidence") or {}
    evidence_class = evidence.get("class", "unknown")
    evidence_strength = evidence.get("strength", 0)

    evidence_lines = []

    if evidence_class == "crowd":
        score = trend.get("score") or 0
        comments = trend.get("comment_count") or 0
        ratio = trend.get("upvote_ratio") or 0
        subreddit = trend.get("subreddit") or "unknown"
        evidence_lines.append(
            f"Source: Reddit (r/{subreddit})"
        )
        evidence_lines.append(
            f"Engagement: {score} upvotes, {comments} comments, "
            f"{ratio:.2f} upvote ratio"
        )
        evidence_lines.append(
            "This is real people reacting to real content. "
            "High engagement means this is a live cultural moment."
        )
    elif evidence_class == "search":
        evidence_lines.append(
            f"Source: Search trends ({source})"
        )
        evidence_lines.append(
            "This is a search query, not a conversation. "
            "It may be an event, a schedule, a product, or a topic."
        )
    elif evidence_class == "synthetic":
        evidence_lines.append(
            "Source: AI-generated filler. No real cultural signal."
        )
    else:
        evidence_lines.append(f"Source: {source}")

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "No evidence available."

    prompt = f"""
You are evaluating whether a cultural signal contains a REAL merch
concept for print-on-demand products (t-shirts, mugs, stickers,
posters, etc.).

You are NOT evaluating whether the title works as a slogan.
Titles are raw material. The merch concept lives inside them.

---

TREND TITLE:
"{title}"

EVIDENCE:
{evidence_block}

---

Your job: decide if there is a *concept* here that could become
differentiated merch, even if the title itself would need rephrasing.

Return STRICT JSON only:

{{
  "keep": true or false,
  "productability_score": 0-100,
  "reason": "short explanation",
  "category": "Humor | Identity | Meme | Subculture | Emotion | Situational | Weak"
}}

---

KEEP when the underlying idea could become merch, for example:

- Humor or irony that a specific community would recognize
  (e.g. "I wish all cops were as chill as these guys" →
   "Chill Cop Energy" merch)
- Identity or subculture signals
  (e.g. "lesbian space princess" → LGBTQ+ sci-fi niche merch)
- Relatable emotional moments
  (e.g. "Celebrating three months of sobriety" → sobriety milestone merch)
- Meme potential with clear remixability
  (e.g. "Humanity 1 x 0 Robot" → AI-vs-humans humor merch)

REJECT when the signal is fundamentally not merch-shaped:

- Sports scores, fixtures, or team schedules
  (e.g. "yankees vs mets", "barcelona schedule")
- News events, politics, or tragedies
- Personal one-off stories with no broader resonance
  (e.g. "Nest cam notified me of a break-in attempt today")
- Bare proper nouns with no concept attached
  (e.g. "Zac Efron", "philadelphia 76ers")
- AI-generated filler that mimics a trend but contains no real idea

---

Additional guidance:

- If the evidence shows strong engagement (Reddit with high upvotes
  and comments), give the trend the benefit of the doubt. Real people
  reacted to it, which means there's something culturally real here —
  even if the title alone looks thin.
- If the evidence is a search query with no engagement data, be
  more skeptical. Search queries are often events, not concepts.
- A productability_score above 60 should generally correspond to
  keep=true. A score below 40 should correspond to keep=false.
  Scores in between are judgment calls.

Return JSON only. No prose, no code fences.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        content = response.choices[0].message.content.strip()

        # Strip code fences if the model emits them
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()

        data = json.loads(content)

        if not data.get("keep", False):
            return None

        trend["productability"] = data
        return trend

    except Exception as e:
        print(f"⚠️ Product gate failed for '{title}': {e}")
        return None