import os
from openai import OpenAI
import html
import json
from utils import normalize_for_pdf, normalize_watchlist_for_pdf, extract_display_signals, normalize_hml

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

Important positioning:
Daily Merch Scout helps creators save research time by surfacing cultural trends
with potential merch opportunities.

It does NOT guarantee sales or winning products. Success depends on the creator’s
design execution, timing, and platform strategy.

The messaging should gently remind readers that the tool helps them discover
ideas faster, but they still bring the creativity.

1. INTRO
- 1 to 2 sentences
- energetic, smart, friendly
- makes reader excited to browse today's ideas

2. OUTRO
- 1 to 2 sentences
- warm signoff
- remind users creativity + execution matter
- mention trademarks lightly
- no selling
- no mention of paid tier

Style:
- Human
- Slightly witty
- Helpful
- No corporate fluff

Email should be:
- Friendly, playful, slightly witty
- Casual, human, not corporate
- Light emoji usage (max 2)

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
    trend_titles = [t.get("merch_headline", "") for t in trends[:4]]
    titles_text = "; ".join(trend_titles)

    prompt = f"""
You are writing a short email for creative merch sellers in the Merch Scout brand voice.

Context:
These are culture-based merch ideas with full Builder edition details.
Trend examples: {titles_text}

Important positioning:
Daily Merch Scout helps creators save research time by surfacing cultural trends
with potential merch opportunities.

It does NOT guarantee sales or winning products. Success depends on the creator’s
design execution, timing, and platform strategy.

The messaging should gently remind readers that the tool helps them discover
ideas faster, but they still bring the creativity.

Tier 2 email should be:
- Friendly, playful, slightly witty
- Casual, human, not corporate
- Light emoji usage (max 1)
- Give 1–2 sentences intro
- Give 1–2 sentences outro
- Outro should include a reminder to check trademarks
- Outro should include a light, subtle conclusion to the email
- Outro should include a reminder that the attached Merch Brief includes things like: trend signls, buyer psychology, target audience, design direction, and niche variations
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

def generate_tier1_email(date_str, trends, max_trends=4, watchlist=None, total_raw_trends=None, total_trends_qualified=None):
    """
    Generates the Tier 1 Merch Scout email.
    - Uses friendly intro/outro from AI
    - Formats each trend with Tier 2 email styling (tables, spacing)
    - Shows top N trends and mentions watchlist count
    """
    intro, outro = generate_tier1_intro_outro(trends, date_str)

    from utils import normalize_for_pdf

    normalized_trends = [normalize_for_pdf(t) for t in trends]

    html_parts = []

    # ---- INTRO ----
    html_parts.append(f"<p>{intro}</p>")

    if total_raw_trends and total_trends_qualified:
        html_parts.append(f"""
        <p><b>📊 Today’s scan:</b><br>
        {total_raw_trends} culture trends analyzed<br>
        {total_trends_qualified} trends qualified for merch potential</p>
        """)

    # ---- TOP TRENDS ----
    for i, trend in enumerate(normalized_trends[:max_trends], 1):
        title = trend.get("merch_headline", "Untitled trend")
        #slogan = trend.get("slogan", "—")
        merch_angle = trend.get("core_insight", "")
        products = trend.get("secondary_products", [])
        design = trend.get("design_direction","No designs found")
        priority = trend.get("execution_priority","")

        #merch_html = "<br>".join(f"• {html.escape(item)}" for item in merch_ideas) if merch_ideas else "• Mug<br>• T-shirt"

        merch_html = "<br>".join(
            f"• {html.escape(p)}" for p in products[:2]
        ) if products else "• T-shirt<br>• Mug"
        #opportunity = tier1_opportunity_line(trend)

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
                        <strong>Why it works</strong><br>
                        {html.escape(merch_angle)}
                    </p>
                    <p style="margin: 0 0 12px 0; font-size: 14px;">
                        <strong>Quick design idea</strong><br>
                        {html.escape(design)}
                    </p>
                    <p style="margin: 0 0 12px 0; font-size: 14px;">
                        <strong>Priority</strong><br>
                        {html.escape(priority)}
                    </p>
                    <p style="margin: 0; font-size: 14px;">
                        <strong>Best merch fit</strong><br>
                        {merch_html}
                    </p>
                </td>
            </tr>
            </table>
        """)

    # ---- PRO CTA BLOCK ----
    remaining = max(0, (total_trends_qualified or len(trends)) - max_trends)

    html_parts.append(f"""
    <table width="100%" cellpadding="0" cellspacing="0"
    style="margin: 32px 0; background:#f8f8f8; border:1px solid #e5e5e5; border-radius:8px;">
    <tr>
    <td style="padding:20px; font-family:Arial,sans-serif;">

    <p style="margin:0 0 10px 0; font-size:18px; font-weight:bold;">
    👀 What Pro Members See Today
    </p>

    <p style="margin:0 0 10px 0; font-size:14px; line-height:1.5;">
    + {remaining} additional filtered merch opportunities<br>
    + Buyer psychology insights<br>
    + Niche variations<br>
    + Trend signals & timing data<br>
    + Daily PDF playbook
    </p>

    <p style="margin:0; font-size:14px;">
    Upgrade to <strong>Merch Scout Builder</strong> and skip the guesswork.
    </p>

    </td>
    </tr>
    </table>
    """)

    # ---- AI OUTRO ----
    html_parts.append(f"<p>{outro}</p>")

    html_parts.append("""
    <p>☕ Until next time,<br>
    <strong>Daily Merch Scout</strong></p>
    """)

    return "\n".join(html_parts)

def generate_tier2_email(date_str, trends, watchlist=None, total_raw_trends=None, total_trends_qualified=None):
    """
    Generates the Tier 2 Merch Scout Builder Edition email.
    Cleaner premium layout + top deep dive + watchlist + PDF reminder.
    """

    from utils import normalize_for_pdf, normalize_watchlist_for_pdf

    normalized_trends = [normalize_for_pdf(t) for t in trends]

    intro, outro = generate_tier2_intro_outro(normalized_trends, date_str)

    total_raw = total_raw_trends or len(trends)
    total_qualified = total_trends_qualified or len(trends)

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height:1.55; color:#222; max-width:700px; margin:auto;">

    <p>{intro}</p>

    <p><b>📊 Today’s scan:</b><br>
    {total_raw} culture trends analyzed<br>
    {total_qualified} trends qualified for merch potential</p>

    <hr style="margin:24px 0;">
    """

    # ==================================================
    # TOP TREND (Deep Dive)
    # ==================================================
    if normalized_trends:

        top = normalized_trends[0]

        title = top.get("merch_headline", "Untitled Trend")
        insight = top.get("core_insight", "")
        buyer = top.get("buyer_psychology", "")
        design = top.get("design_direction", "")
        risk = top.get("risk_level", "")
        priority = top.get("execution_priority", "")
        products = top.get("secondary_products", [])[:4]

        niche_variations = top.get("niche_variations", [])

        product_html = "".join([f"<li>{p}</li>" for p in products])

        html += f"""
        <h2 style="margin-bottom:8px;">🚀 Priority Launch Today</h2>

        <div style="border:1px solid #ddd; padding:18px; margin-bottom:28px; border-radius:8px;">

        <h3 style="margin-top:0;">1. {title}</h3>

        <p><b>Risk Level:</b> {risk}<br>
        <b>Execution Priority:</b> {priority}</p>

        <p><b>Why It Sells</b><br>{insight}</p>

        <p><b>Buyer Psychology</b><br>{buyer}</p>

        <p><b>Best Products</b></p>
        <ul>{product_html}</ul>

        <p><b>Design Direction</b><br>{design}</p>
        """

        if niche_variations:
            html += "<p><b>Niche Variations</b></p>"

            for nv in niche_variations[:3]:
                niche_name = nv.get("niche_name", "")
                subtext = nv.get("subtext", "")
                html += f"""
                <p style="margin:0 0 10px 0;">
                <b>{niche_name}</b><br>
                {subtext}
                </p>
                """

        diff = top.get("differentiation_strategy", "")
        if diff:
            html += f"""
            <p><b>Differentiation Strategy</b><br>{diff}</p>
            """

        html += "</div>"

    # ==================================================
    # TRENDS 2 + 3 (Lighter Detail)
    # ==================================================
    if len(normalized_trends) > 1:

        html += "<h2 style='margin-bottom:12px;'>🔥 Other Strong Opportunities</h2>"

        for idx, trend in enumerate(normalized_trends[1:3], start=2):

            title = trend.get("merch_headline", "")
            insight = trend.get("core_insight", "")
            design = trend.get("design_direction", "")
            risk = trend.get("risk_level", "")
            priority = trend.get("execution_priority", "")
            products = trend.get("secondary_products", [])[:3]

            product_html = "".join([f"<li>{p}</li>" for p in products])

            html += f"""
            <div style="border-top:1px solid #eee; padding-top:16px; margin-bottom:20px;">

            <h3>{idx}. {title}</h3>

            <p><b>Why It Sells</b><br>{insight}</p>

            <p><b>Risk Level:</b> {risk}<br>
            <b>Execution Priority:</b> {priority}</p>

            <p><b>Best Products</b></p>
            <ul>{product_html}</ul>

            <p><b>Design Direction</b><br>{design}</p>

            </div>
            """

    # ==================================================
    # WATCHLIST
    # ==================================================
    if watchlist:

        html += """
        <hr style="margin:28px 0;">
        <h2>👀 Watch List</h2>
        <ul style="padding-left:20px;">
        """

        for item in watchlist:
            w = normalize_watchlist_for_pdf(item)
            title = w.get("merch_headline", "Untitled")
            html += f"<li style='margin-bottom:8px;'>{title}</li>"

        html += "</ul>"

    # ==================================================
    # PDF BLOCK
    # ==================================================
    html += """
    <div style="background:#f8f8f8; border:1px solid #e5e5e5; padding:18px; margin:30px 0; border-radius:8px;">

    <p style="margin-top:0;"><b>📎 Today’s Builder PDF Included</b></p>

    <p style="margin-bottom:0;">
    ✅ Top 5 expanded opportunities<br>
    ✅ Buyer psychology insights<br>
    ✅ Niche variations<br>
    ✅ Product recommendations<br>
    ✅ Design direction ideas<br>
    ✅ Additional watch list signals
    </p>

    </div>
    """

    # ==================================================
    # OUTRO
    # ==================================================
    html += f"""
    <p>{outro}</p>

    <p style="margin-top:28px; font-style:italic; color:#555;">
    ☕ Until next time,<br>
    <strong>Daily Merch Scout — Builder Edition</strong>
    </p>

    </body>
    </html>
    """

    return html


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








