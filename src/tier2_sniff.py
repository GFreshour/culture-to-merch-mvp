import json
import time

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def run_tier2_sniff(trend, client):
    """
    Tier-2 commercial sniff test (AI-powered)
    Structured for ranking + stratification
    """

    prompt = f"""
You are evaluating a cultural trend for print-on-demand merch viability.

Trend title:
"{trend.get('title')}"

Return STRICT JSON only, like this example:

{{
  "commercial_score": 0,
  "buyer_intent": "identity | humor | giftable | community | sarcasm | motivation",
  "trend_type": "evergreen | cyclical | viral_spike | cultural_moment | slow_build",
  "audience_size": "high | medium | low",
  "saturation_risk": "low | medium | high",
  "ip_risk": "none | moderate | high",
  "longevity": "short | medium | long",
  "confidence": 0,
  "reasoning": {{
    "why_it_works": "",
    "main_risk": "",
    "who_it_resonates_with": "",
    "why_people_would_buy": ""
  }}
}}
"""
    for attempt in range(1, MAX_RETRIES + 1): # Start retry loop

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()

            if not content:
                print(f"⚠️ Tier-2 empty response (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
                continue

            try:
                data = json.loads(content)

            except json.JSONDecodeError:
                print(f"⚠️ Tier-2 JSON parse error (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
                

            # Ensure all required keys exist (safe defaults)
            data.setdefault("commercial_score", 0)
            data.setdefault("buyer_intent", "identity")
            data.setdefault("trend_type", "slow_build")
            data.setdefault("audience_size", "medium")
            data.setdefault("saturation_risk", "medium")
            data.setdefault("ip_risk", "none")
            data.setdefault("longevity", "medium")
            data.setdefault("confidence", 0)
            data.setdefault("reasoning", {
                "why_it_works": "",
                "main_risk": "",
                "who_it_resonates_with": "",
                "why_people_would_buy": ""
            })

            return data

        except Exception as e:
            print(f"⚠️ Tier-2 API error (attempt {attempt}/{MAX_RETRIES}): {e}")
        
        time.sleep(RETRY_DELAY)
    
    print(f"⚠️ Tier2 sniff ultimately failed for '{trend.get('title')}'")

    return {
        "commercial_score": 0,
        "buyer_intent": "identity",
        "trend_type": "slow_build",
        "audience_size": "medium",
        "saturation_risk": "medium",
        "ip_risk": "none",
        "longevity": "medium",
        "confidence": 0,
        "reasoning": {
            "why_it_works": "",
            "main_risk": "",
            "who_it_resonates_with": "",
            "why_people_would_buy": ""
        }
    }