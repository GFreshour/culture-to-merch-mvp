import os
from openai import OpenAI
import html
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_tier1_intro_outro(trends, date_str):
    """
    Generates a friendly, playful intro and outro for Tier 1 emails.
    Includes subtle upsell to Tier 2 (Builder edition) and trademark reminder.
    """
    trend_titles = [t.get("slogan", "") for t in trends[:4]]
    titles_text = "; ".join(trend_titles)

    prompt = f"""
You are writing a short email for creative merch sellers in the Merch Scout brand voice.

Context:
These are culture-based merch ideas inspired by recent trends.
Trend examples: {titles_text}

TASK:
1. Write a friendly, playful INTRO (1–2 sentences).
2. Write a warm, encouraging OUTRO (2–3 sentences), including:
    - Outro should subtly upsell Tier 2 (Builder edition) without being pushy
    - Outro should include a reminder to check trademarks
    - Outro should include a light, subtle conclusion to the email

Tier 1 email should be:
- Friendly, playful, slightly witty
- Casual, human, not corporate
- Light emoji usage (max 1)

Tier 2 (Builder edition) includes:
- Alternate slogans for each trend
- Design ideas
- Competition signals and trend strength
- Keywords ready to list
- Risks / notes

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
        data = json.loads(text)
        return data.get("intro", ""), data.get("outro", "")
    except Exception as e:
        print("⚠️ AI Tier 1 intro/outro failed:", e)
        return (
            "A few culture → merch ideas stood out recently. Here are the ones worth a quick look.",
            "If one of these sparked something, that’s a good day’s work. Check trademarks before listing and have fun exploring these ideas!"
        )


def generate_tier2_intro_outro(trends, date_str):
    """
    Generates a friendly, professional intro and outro for Tier 2 emails.
    No upsell needed, only encouragement, trend context, and trademark reminder.
    """
    trend_titles = [t.get("slogan", "") for t in trends[:4]]
    titles_text = "; ".join(trend_titles)

    prompt = f"""
You are writing a short email for creative merch sellers in the Merch Scout brand voice.

Context:
These are culture-based merch ideas with full Builder edition details.
Trend examples: {titles_text}

Tier 2 email should be:
- Friendly, playful, slightly witty
- Casual, human, not corporate
- Light emoji usage (max 1)
- Give 1–2 sentences intro
- Give 1–2 sentences outro
- Outro should include a reminder to check trademarks
- Outro should include a light, subtle conclusion to the email
- Do NOT mention Tier 3 or upsell

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
        data = json.loads(text)
        return data.get("intro", ""), data.get("outro", "")
    except Exception as e:
        print("⚠️ AI Tier 2 intro/outro failed:", e)
        return (
            "Here’s a closer look at today’s culture → merch ideas, broken down for your creative edge.",
            "Check trademarks before listing. Hope these insights spark some fun merch creations!"
        )

from ai_insights import generate_tier1_intro_outro

def tier1_opportunity_line(trend: dict) -> str:
    """
    Returns a teaser line based on hidden signals.
    """

    signals = trend.get("trend_signals", {})
    sniff = trend.get("tier2_sniff", {})

    merch = (signals.get("merch_potential") or "").lower()
    spread = (signals.get("cross_platform_spread") or "").lower()
    verdict = (sniff.get("verdict") or "").lower()
    score = sniff.get("sniff_score")

    # ---------- HIGH OPPORTUNITY ----------
    if verdict == "high" or (isinstance(score, int) and score >= 75):
        return "🔹 Strong opportunity — worth acting quickly"

    if merch == "high" and spread in ("medium", "high"):
        return "🔹 Early-stage trend with strong merch potential"

    # ---------- SOLID / WATCH ----------
    if merch in ("medium", "high"):
        return "🔹 Gaining traction — worth watching closely"

    if spread == "high":
        return "🔹 Broad appeal with room for creative angles"

    # ---------- SAFE DEFAULT ----------
    return "🔹 Interesting concept with merch potential"

def generate_tier1_email(date_str, trends, max_trends=4):
    intro, outro = generate_tier1_intro_outro(trends, date_str)

    html_parts = []

    # ---- INTRO ----
    html_parts.append(f"""
    <p>{intro}</p>
    """)

    # ---- TRENDS ----
    for i, trend in enumerate(trends[:max_trends], 1):
        title = trend.get("title", "Untitled trend")
        slogan = trend.get("slogan", "—")
        merch_angle = trend.get("why_it_works", "")
        merch_ideas = trend.get("merch_ideas", [])

        # Turn merch ideas into a readable list
        merch_html = "<br>".join(f"• {html.escape(item)}" for item in merch_ideas) if merch_ideas else "• Mug<br>• T-shirt"

        opportunity = tier1_opportunity_line(trend)

        html_parts.append(f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                style="margin: 28px 0; border-top: 2px solid #e5e5e5;">
            <tr>
                <td style="padding-top: 16px; font-family: Arial, sans-serif;">

                <p style="margin: 0 0 10px 0; font-size: 19px; font-weight: bold; color: #111;">
                    🔥 <strong>Trend #{i}</strong>
                </p>

                <p style="margin: 0 0 10px 0; font-size: 18px; font-weight: bold; color: #111;">
                    {html.escape(slogan)}
                </p>
                <p style="margin: 0 0 10px 0; font-size: 13px; color: #666;">
                    {html.escape(opportunity)}
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
      ☕ Until next time,<br>
      <strong>Daily Merch Scout</strong>
    </p>
    """)

    return "\n".join(html_parts)

def generate_tier2_email(date_str, trends, max_trends=4):
    intro, outro = generate_tier2_intro_outro(trends, date_str)

    html_parts = []

    # ---------- Helpers ----------
    def score_display(score):
        """Return colored score text"""
        try:
            score = int(score)
        except:
            return "⚪️ —"

        if score >= 75:
            return f"🟢 {score}"
        elif score >= 50:
            return f"🟡 {score}"
        else:
            return f"🔴 {score}"

    def confidence_display(conf):
        try:
            conf = int(conf)
            return f"{conf}%"
        except:
            return "—"

    def safe_text(val, default="—"):
        if val is None:
            return default
        val = str(val).strip()
        return val if val else default

    # ---------- INTRO ----------
    html_parts.append(f"""
    <p>{intro}</p>
    """)

    # ---------- TRENDS ----------
    for i, trend in enumerate(trends[:max_trends], 1):
        title = trend.get("title", "Untitled trend")
        slogan = trend.get("slogan", "—")
        merch_angle = trend.get("why_it_works", "")
        merch_ideas = trend.get("merch_ideas", [])

        signals = trend.get("trend_signals", {})
        rationale = trend.get("rationale", "—")

        # ---------- Tier-2 Sniff ----------
        if "tier2_sniff" in trend and trend["tier2_sniff"]:
            sniff = trend["tier2_sniff"]

            signals["sniff_score"] = sniff.get("sniff_score")
            signals["sniff_verdict"] = sniff.get("verdict")
            signals["sniff_confidence"] = sniff.get("confidence")

            rationale = sniff.get("why_it_works", rationale)
        else:
            signals["sniff_score"] = None
            signals["sniff_verdict"] = None
            signals["sniff_confidence"] = None

        rationale = signals.get("rationale") or "—"

        merch_html = "<br>".join(
            f"• {html.escape(item)}" for item in merch_ideas
        ) if merch_ideas else "• Mug<br>• T-shirt"

        # ---------- Trend HTML ----------

        aud_emoji, aud_label = format_audience_size(
            signals.get("cross_platform_spread")
        )

        html_parts.append(f"""
            <table width="100%" cellpadding="0" cellspacing="0"
                style="margin: 28px 0; border-top: 2px solid #e5e5e5;">
            <tr>
                <td style="padding-top: 16px; font-family: Arial, sans-serif;">

                <p style="margin: 0 0 10px 0; font-size: 19px; font-weight: bold; color: #111;">
                    🔥 <strong>Trend #{i}</strong>
                </p>

                <p style="margin: 0 0 6px 0; font-size: 18px; font-weight: bold; color: #111;">
                    {html.escape(slogan)}
                </p>

                <!-- 🛒 POD Builder Signals -->
                <table width="100%" cellpadding="6" cellspacing="0"
                    style="font-size: 13px; border-collapse: collapse; background: #fafafa; border-radius: 6px; margin: 6px 0 12px 0;">

                <tr>
                    <td><strong>Easy to Put on Products</strong></td>
                    <td>{signal_badge(signals.get("merch_potential"))}</td>
                </tr>

                <tr>
                    <td><strong>Buzz Right Now</strong></td>
                    <td>{signal_badge(signals.get("hashtag_growth"))}</td>
                </tr>

                <tr>
                    <td><strong>Multiple Design Potential</strong></td>
                    <td>{signal_badge(signals.get("memetic_variations"))}</td>
                </tr>

                <tr>
                    <td><strong>Audience Size</strong></td>
                    <td>{aud_emoji} {html.escape(aud_label)}</td>
                </tr>

                <tr>
                    <td colspan="2" style="padding-top: 8px; border-top: 1px solid #e5e5e5;"></td>
                </tr>

                <tr>
                    <td><strong>Chance of Selling</strong></td>
                    <td>{score_badge(signals.get("sniff_score"))} / 100</td>
                </tr>

                <tr>
                    <td><strong>Worth Making Now?</strong></td>
                    <td>{signal_badge(normalize_level(signals.get("sniff_verdict")))}</td>
                </tr>

                <tr>
                    <td><strong>Signal Strength</strong></td>
                    <td>{format_percent(signals.get("sniff_confidence"))}</td>
                </tr>

                <tr>
                    <td colspan="2"
                        style="padding-top: 6px; font-size: 12px; color: #555;">
                        {html.escape(outlook_interpretation(signals.get("sniff_score")))}
                    </td>
                </tr>

                </table>

        """)
        # Alternate slogans (if any)
        alternates = trend.get("alternates", [])
        if alternates:
            alternates_html = "<ul style='margin: 0 0 12px 16px; padding: 0; font-size: 14px;'>"
            for alt in alternates:
                alternates_html += f"<li>{html.escape(alt)}</li>"
            alternates_html += "</ul>"

            html_parts.append(f"""
                <p style="margin: 0 0 12px 0; font-size: 14px;">
                    <strong>Alternate slogans:</strong>
                </p>
                {alternates_html}
            """)
            html_parts.append(f"""
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

    # ---------- CTA ----------
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

    # ---------- OUTRO ----------
    html_parts.append(f"""
    <p>{outro}</p>

    <p>
      ☕ Until next time,<br>
      <strong>Daily Merch Scout</strong>
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
        return "⚪️ —"

    v = str(value).strip().lower()

    # Normalize common AI variations
    if "high" in v or "strong" in v or "mainstream" in v:
        label = "High"
    elif "medium" in v or "moderate" in v or "emerging" in v:
        label = "Medium"
    elif "low" in v or "weak" in v or "niche" in v:
        label = "Low"
    else:
        return f"⚪️ {value}"

    emoji = SIGNAL_EMOJI.get(label, "⚪️")
    return f"{emoji} {label}"

def outlook_interpretation(score):
    """
    Returns a short human-friendly interpretation
    for the Sales Outlook Score.
    """
    try:
        score = int(score)
    except:
        return ""

    if score >= 80:
        return "🔥 Strong commercial potential — worth prioritizing"
    elif score >= 60:
        return "✅ Solid opportunity — good listing candidate"
    elif score >= 40:
        return "⚖️ Viable with strong design execution"
    elif score >= 20:
        return "⚠️ Niche appeal — test before scaling"
    else:
        return "👉 Likely to sell only with a strong design angle"

def normalize_level(value):
    """
    Standardizes AI output to: High / Medium / Low
    """
    if not value:
        return "—"

    v = str(value).strip().lower()

    if v in ("high", "strong"):
        return "High"

    if v in ("medium", "moderate", "median"):
        return "Medium"

    if v in ("low", "weak"):
        return "Low"

    return value

def score_badge(score):
    """
    Converts numeric score (0–100) into color badge.
    """
    try:
        s = int(score)
    except:
        return f"⚪️ {score}"

    if s >= 70:
        icon = "🟢"
    elif s >= 40:
        icon = "🟡"
    else:
        icon = "🔴"

    return f"{icon} {s}"

def format_percent(value):
    if value is None or value == "":
        return "—"

    try:
        v = int(value)
        return f"{v}%"
    except:
        return str(value)

def format_audience_size(size: str) -> tuple[str, str]:
    """
    Returns (emoji, label) for audience size.
    Input should be one of: small, medium, large
    """

    size = (size or "").lower()

    mapping = {
        "low":  ("🟡", "Small"),
        "medium": ("🟡", "Medium"),
        "high":  ("🟢", "Large"),
    }

    return mapping.get(size, ("⚪️", "Unknown"))








