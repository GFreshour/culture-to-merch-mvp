import os
from openai import OpenAI
import html
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_tier1_intro_outro(trends, date_str):
    """
    Generates a short, playful intro and outro for Tier 1 emails.
    Uses existing enriched trend data for context.
    """

    trend_titles = [t.get("title", "") for t in trends[:4]]
    titles_text = "; ".join(trend_titles)

    prompt = f"""
You are writing a short email for creative merch sellers.

Context:
These are culture-based merch ideas inspired by recent trends.
Trend examples: {titles_text}

TASK:
1. Write a friendly, playful INTRO (1–2 sentences).
2. Write a warm, encouraging OUTRO (1–2 sentences).

RULES:
- Do NOT mention Reddit or social platforms
- Keep it casual and human
- No emojis overload (1 max)
- No salesy language
- Avoid generic phrases like "unlock your creativity"

Return valid JSON only:
{{
  "intro": "",
  "outro": ""
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        text = response.choices[0].message.content
        #print("Raw AI intro/outro response:", text)  # Debug print

        data = json.loads(text)
        #print("Parsed AI intro/outro JSON:", data)  # Debug print
        return data.get("intro", ""), data.get("outro", "")

    except Exception as e:
        print("⚠️ AI intro/outro failed:", e)
        return (
            "A few culture → merch ideas stood out recently. Here are the ones worth a quick look.",
            "If one of these sparked something, that’s a good day’s work. Always double-check trademarks before listing."
        )


# analyze_trend is a legacy / future helper (not used in run())
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

from ai_insights import generate_tier1_intro_outro

def generate_tier1_email(date_str, trends, max_trends=4):
    intro, outro = generate_tier1_intro_outro(trends, date_str)

    html_parts = []

    # ---- INTRO ----
    html_parts.append(f"""
    <p><strong>Hey there!</strong></p>
    <p>{intro}</p>
    """)

    # ---- TRENDS ----
    for i, trend in enumerate(trends[:max_trends], 1):
        title = trend.get("title", "Untitled trend")
        slogan = trend.get("slogan", "—")
        merch_angle = trend.get("why_it_works", "")
        merch_ideas = trend.get("merch_ideas", [])

        #<table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0; border-top: 1px solid #e5e5e5;">


        # Turn merch ideas into a readable list
        merch_html = "<br>".join(f"• {html.escape(item)}" for item in merch_ideas) if merch_ideas else "• Mug<br>• T-shirt"

        html_parts.append(f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                style="margin: 28px 0; border-top: 2px solid #e5e5e5;">
            <tr>
                <td style="padding-top: 16px; font-family: Arial, sans-serif;">

                <p style="margin: 0 0 10px 0; font-size: 19px; font-weight: bold; color: #111;">
                    🔥 <strong>Trend #{i}</strong>
                </p>

                <p style="margin: 0 0 10px 0; font-size: 18px; font-weight: bold; color: #111;">
                    {html.escape(title)}
                </p>

                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    ☕ <strong>Slogan</strong><br>
                    <em>{html.escape(slogan)}</em>
                </p>

                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    <strong>Why it works</strong><br>
                    {html.escape(merch_angle)}
                </p>

                <p style="margin: 0; font-size: 14px;">
                    <strong>Best merch fit</strong><br>
                    {merch_html}
                </p>

                </td>
            </tr>
            </table>
            """)

    html_parts.append(f"""
        <table width="100%" cellpadding="0" cellspacing="0"
            style="margin: 32px 0; border-top: 2px dashed #e5e5e5;">
        <tr>
            <td style="padding-top: 16px; font-size: 14px; color: #333; line-height: 1.5;">
            <strong>Want to go a level deeper?</strong><br><br>
            The Builder edition breaks these ideas down further — alternate slogans,
            design direction, competition signals, and keyword-ready details you can
            actually list from.<br><br>
            No pressure. Just a heads-up if today’s ideas sparked something.
            </td>
        </tr>
        </table>
        """)

    # ---- OUTRO ----
    html_parts.append(f"""
    <p>{outro}</p>

    <p>
      Friendly reminder to double-check trademarks or protected phrases
      before listing anything for sale.
    </p>

    <p>
      ☕ Until next time,<br>
      <strong>Daily Merch Bot</strong>
    </p>
    """)

    return "\n".join(html_parts)

def generate_tier2_email(date_str, trends, max_trends=4):
    intro, outro = generate_tier1_intro_outro(trends, date_str)

    html_parts = []

    # ---- INTRO ----
    html_parts.append(f"""
    <p><strong>Hey there!</strong></p>
    <p>{intro}</p>
    """)

    # ---- TRENDS ----
    for i, trend in enumerate(trends[:max_trends], 1):
        title = trend.get("title", "Untitled trend")
        slogan = trend.get("slogan", "—")
        merch_angle = trend.get("why_it_works", "")
        merch_ideas = trend.get("merch_ideas", [])

        # ---- Pull trend signals ----
        signals = trend.get("trend_signals", {})
        rationale = trend.get("rationale", "—")

        print("EMAIL SIGNALS (after extraction):", signals)
        print("EMAIL SIGNALS KEYS:", list(signals.keys()))
        print("AI ENRICHMENT KEYS:", trend.get("ai_enrichment", {}).keys())

        rationale = signals.get("rationale")
        if not rationale or not str(rationale).strip():
            rationale = "—"

        print("EMAIL SIGNALS:", signals)

        merch_html = "<br>".join(f"• {html.escape(item)}" for item in merch_ideas) if merch_ideas else "• Mug<br>• T-shirt"

        # ---- Trend HTML ----
        html_parts.append(f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                style="margin: 28px 0; border-top: 2px solid #e5e5e5;">
            <tr>
                <td style="padding-top: 16px; font-family: Arial, sans-serif;">

                <p style="margin: 0 0 10px 0; font-size: 19px; font-weight: bold; color: #111;">
                    🔥 <strong>Trend #{i}</strong>
                </p>

                <p style="margin: 0 0 6px 0; font-size: 18px; font-weight: bold; color: #111;">
                    {html.escape(title)}
                </p>

                <!-- 🟢🟡🔴 Trend Signals Table -->
                <table width="100%" cellpadding="6" cellspacing="0"
                    style="font-size: 13px; border-collapse: collapse; background: #fafafa; border-radius: 6px; margin: 6px 0 12px 0;">
                <tr>
                    <td><strong>Merch Potential</strong></td>
                    <td>{signal_badge(signals.get("merch_potential"))}</td>
                </tr>
                <tr>
                    <td><strong>Hashtag Growth</strong></td>
                    <td>{signal_badge(signals.get("hashtag_growth"))}</td>
                </tr>
                <tr>
                    <td><strong>Memetic Variations</strong></td>
                    <td>{signal_badge(signals.get("memetic_variations"))}</td>
                </tr>
                <tr>
                    <td><strong>Cross-Platform Spread</strong></td>
                    <td>{signal_badge(signals.get("cross_platform_spread"))}</td>
                </tr>
                </table>

                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    ☕ <strong>Slogan</strong><br>
                    <em>{html.escape(slogan)}</em>
                </p>

                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    <strong>Why it works</strong><br>
                    {html.escape(merch_angle)}
                </p>

                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    <strong>Why this matters now</strong><br>
                    {html.escape(rationale)}
                </p>

                <p style="margin: 0; font-size: 14px;">
                    <strong>Best merch fit</strong><br>
                    {merch_html}
                </p>

                </td>
            </tr>
            </table>
        """)

    # ---- CTA ----
    html_parts.append(f"""
        <table width="100%" cellpadding="0" cellspacing="0"
            style="margin: 32px 0; border-top: 2px dashed #e5e5e5;">
        <tr>
            <td style="padding-top: 16px; font-size: 14px; color: #333; line-height: 1.5;">
            <strong>Want the full breakdown?</strong><br><br>
            Your attached Builder PDF includes deeper signal analysis,
            platform patterns, and merch execution notes for all 20 trends.
            </td>
        </tr>
        </table>
    """)

    # ---- OUTRO ----
    html_parts.append(f"""
    <p>{outro}</p>

    <p>
      Friendly reminder to double-check trademarks or protected phrases
      before listing anything for sale.
    </p>

    <p>
      ☕ Until next time,<br>
      <strong>Daily Merch Bot</strong>
    </p>
    """)

    return "\n".join(html_parts)



# Map trend signal levels to emojis
SIGNAL_EMOJI = {
    "High": "🟢",
    "Medium": "🟡",
    "Low": "🔴",
    "Mainstream": "🟢",
    "Emerging": "🟡",
    "Niche": "🔴",
}

def signal_badge(value):
    if not value:
        return "⚪️"

    value = str(value).strip()

    emoji = SIGNAL_EMOJI.get(value)
    if not emoji:
        return f"⚪️ {value}"

    return f"{emoji} {value}"








