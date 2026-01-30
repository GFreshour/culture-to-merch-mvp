import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_trend(trend_name, context=""):
    prompt = f"""
You are a merch trend analyst.

Trend: {trend_name}
Context: {context}

Return:
1. Why this trend works emotionally (2–3 sentences)
2. 2–3 merch angles (bulleted)
3. Best product formats
4. Any risks or things to avoid

Be concise. Avoid fluff.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response.choices[0].message.content
