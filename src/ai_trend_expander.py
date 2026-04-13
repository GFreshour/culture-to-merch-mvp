import json


def expand_trends_with_ai(client, existing_trends, target_count=15):
    """
    Uses AI to expand a small set of trends into more trend-like phrases.
    Returns list of trend dicts in SAME format as pipeline expects.
    """

    if not existing_trends:
        return []

    # Extract base titles (limit to avoid prompt bloat)
    base_trends = [t["title"] for t in existing_trends[:10]]

    prompt = f"""
You are a trend discovery engine for viral merch ideas.

We currently have a small set of early signals:

{base_trends}

Generate SPECIFIC, concrete trend phrases (not generic inspiration).

GOOD examples:
- "Corporate burnout humor"
- "AI replacing networking"
- "Festival outfit identity"
- "Investing like a beginner again"

BAD examples:
- "Chase your dreams"
- "Be yourself"
- "Stay motivated"

RULES:
- Return ONLY a JSON array
- Each item must be a SHORT phrase (3–10 words)
- No questions
- No explanations
- No hashtags
- No duplicates of the input
- Focus on ideas that could work on t-shirts, mugs, or stickers

Return {target_count} new trends.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        # ---- SAFE JSON PARSE ----
        try:
            generated = json.loads(content)
        except json.JSONDecodeError:
            print("⚠️ AI returned invalid JSON, attempting cleanup...")

            # basic cleanup fallback
            content_clean = content.strip("```json").strip("```").strip()
            generated = json.loads(content_clean)

        results = []
        for t in generated:
            if not isinstance(t, str):
                continue

            title = t.strip()
            if not title:
                continue

            results.append({
                "title": title,
                "source": "ai_expand",
                "score": 0
            })

        print(f"🤖 AI expanded {len(results)} additional trends")

        return results

    except Exception as e:
        print(f"❌ AI trend expansion failed: {e}")
        return []