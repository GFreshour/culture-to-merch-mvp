import json

def run_tier2_sniff(trend, client):
    """
    Tier-2 commercial sniff test (AI-powered) with safe JSON parsing
    """
    prompt = f"""
You are evaluating a cultural trend for print-on-demand merch viability.

Trend title:
"{trend.get('title')}"

Return STRICT JSON only, like this example:
{{
  "sniff_score": 0,
  "verdict": "Low",
  "confidence": 0,
  "explanation": {{
    "why_it_works": "",
    "main_risk": "",
    "who_it_resonates_with": "",
    "why_people_would_buy": ""
  }}
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        content = response.choices[0].message.content.strip()

        # If content is empty, skip
        if not content:
            print(f"⚠️ Tier-2 sniff returned empty for '{trend.get('title')}'")
            return None

        # Force JSON parsing safely
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            print(f"⚠️ Tier-2 sniff invalid JSON for '{trend.get('title')}': {content}")
            return None

        # Ensure all keys exist
        data.setdefault("sniff_score", 0)
        data.setdefault("verdict", "Unknown")
        data.setdefault("confidence", 0)
        data.setdefault("explanation", {
            "why_it_works": "",
            "main_risk": "",
            "who_it_resonates_with": "",
            "why_people_would_buy": ""
        })

        return data

    except Exception as e:
        print(f"⚠️ Tier-2 sniff failed for '{trend.get('title')}': {e}")
        return None




