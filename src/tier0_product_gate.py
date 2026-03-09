import json

def run_productability_gate(trend, client):
    """
    Tier 0 — Fast AI filter:
    Would this phrase realistically work on a POD product?
    """

    title = trend.get("title", "")

    prompt = f"""
You are evaluating text for print-on-demand product potential
(t-shirts, mugs, stickers, posters, etc.).

TEXT:
"{title}"

Answer STRICT JSON only:

{{
  "keep": true or false,
  "productability_score": 0-100,
  "reason": "short explanation",
  "category": "Relatable | Identity | Humor | Situational | Weak"
}}

Guidelines:
- Keep ONLY if it could plausibly sell on a product
- Must work without extra context
- Broad relatability preferred
- Avoid news, personal stories, or one-off events
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        data = json.loads(content)

        if not data.get("keep", False):
            return None

        trend["productability"] = data
        return trend

    except Exception as e:
        print(f"⚠️ Product gate failed for '{title}': {e}")
        return None