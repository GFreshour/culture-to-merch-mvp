import os
import html
import json
import base64
from datetime import datetime, timedelta
from trends_google import get_daily_trends, google_trend_signal
from tier2_sniff import run_tier2_sniff


# analyze_trend is a legacy / future helper (not used in run())
from ai_insights import (
    generate_tier1_email,
    generate_tier2_email,
    format_audience_size,
    signal_badge,
    score_badge,
    normalize_level,
    format_percent,
    outlook_interpretation
)

from trends_reddit import get_reddit_trends

GROUP_ORDER = [
    "Proven Angle",
    "Momentum Play",
    "Niche Opportunity",
    "Wildcard"
]

GROUP_PLACEHOLDER = {
    "Proven Angle":
        "No strong low-risk opportunities surfaced today.",
    "Momentum Play":
        "No high-velocity trends detected at publish time.",
    "Niche Opportunity":
        "No clear niche winners today.",
    "Wildcard":
        "No unusual experimental ideas passed the filters."
}

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from openai import OpenAI

client = OpenAI()

def html_to_pdf(html_path, pdf_path):
    HTML(filename=html_path).write_pdf(pdf_path)


def extract_section(text, label):
    if label not in text:
        return ""

    section = text.split(label + ":")[1]
    for stop in [
        "MERCH_ANGLE:",
        "MUG_SLOGAN:",
        "CANVA_IMAGE_IDEA:",
        "ETSY_KEYWORDS:",
        "RISKS:"
    ]:
        if stop != label and stop in section:
            section = section.split(stop)[0]

    return section.strip()

def normalize_trend_for_email(trend: dict) -> dict:
    """
    Converts AI-enriched trend data into email-friendly fields.
    No AI calls here — pure transformation.
    """

    ai = trend.get("ai_enrichment", {}) or {}
    signals = ai.get("trend_signals", {}) or {}

    merch_angle = ai.get("merch_angle", "").strip()
    slogan = ai.get("slogan", "").strip()
    alternates = ai.get("alternates", [])

    merch_fit = ai.get("merch_fit", {}) or {}

    primary = merch_fit.get("primary")
    secondary = merch_fit.get("secondary", [])
    avoid = merch_fit.get("avoid", [])

    merch_ideas = []

    if primary:
        merch_ideas.append(primary)

    for item in secondary:
        if item not in merch_ideas:
            merch_ideas.append(item)

    # Sensible fallback if AI didn’t return merch_fit
    if not merch_ideas:
        merch_ideas = ["T-shirt", "Mug"]

    return {
        "title": trend.get("title", ""),
        "slogan": slogan,
        "alternates": alternates,
        "why_it_works": merch_angle,
        "merch_ideas": merch_ideas[:3],
        "avoid": avoid,

        # 🔥 THIS IS THE FIX 🔥
        "trend_signals": signals,
        "rationale": signals.get("rationale", ""),

        # ⭐ PASS THROUGH SNIFF DATA
        "tier2_sniff": trend.get("tier2_sniff")
    }


import json

def enrich_trend_with_ai(trend, prompt=None):
    """
    Enrich a single trend using OpenAI.
    If a custom prompt is provided, it will be used; otherwise, the default prompt is built.
    Forces AI to return JSON using the schema with 'design' as a list of dicts.
    """
    if prompt is None:
        prompt = build_ai_prompt(trend)

    prompt += """

Return your response as VALID JSON using EXACTLY this schema:

{
  "merch_angle": "",
  "slogan": "",
  "alternates": [],
  "design": [
    {
      "style": "",
      "layout": "",
      "font_vibe": "",
      "colors": "",
      "graphic": ""
    }
  ],
  "merch_fit": {
    "primary": "",
    "secondary": [],
    "avoid": []
  },
  "keywords": [],
  "risks": "",
  "trend_signals": {{
    "merch_potential": "",
    "hashtag_growth": "",
    "memetic_variations": "",
    "cross_platform_spread": "",
    "search_volume_mentions": "",
    "merch_branding": "",
    "rationale": "",
    "examples": []
}}
}}

Do not include any extra text. Return JSON only.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a merch designer helping sellers turn trends into sellable product ideas."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    raw_text = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw_text)
        return {
            "merch_angle": parsed.get("merch_angle", ""),
            "slogan": parsed.get("slogan", ""),
            "alternates": parsed.get("alternates", []),
            "design": parsed.get("design", []),
            "merch_fit": parsed.get("merch_fit", {
                "primary": "",
                "secondary": [],
                "avoid": []
            }),
            "keywords": parsed.get("keywords", []),
            "risks": parsed.get("risks", ""),
            # <-- NEW: trend signals from AI prompt
            "trend_signals": parsed.get("trend_signals", {
                "merch_potential": "",
                "hashtag_growth": "",
                "memetic_variations": "",
                "cross_platform_spread": "",
                "search_volume_mentions": "",
                "merch_branding": "",
                "rationale": "",
                "examples": []
            })
        }

    except json.JSONDecodeError:
        print("⚠️ OpenAI response was not valid JSON:")
        print(raw_text)
        return {
            "merch_angle": "",
            "slogan": "",
            "alternates": [],
            "design": [],
            "merch_fit": {
                "primary": "",
                "secondary": [],
                "avoid": []
            },
            "keywords": [],
            "risks": "",
            # <-- fallback for trend signals
            "trend_signals": {
                "merch_potential": "",
                "hashtag_growth": "",
                "memetic_variations": "",
                "cross_platform_spread": "",
                "search_volume_mentions": "",
                "merch_branding": "",
                "rationale": "",
                "examples": []
            }
        }


# ---------------- CONFIG ----------------

OUTPUT_DIR = "output"
TOP_N = 20

FROM_EMAIL = "gary_freshour@hotmail.com"
#TO_EMAIL = "daniellefreshour@gmail.com"
TO_EMAILS = [
    "daniellefreshour@gmail.com",
    "garyfreshour@gmail.com"
]

SUBREDDIT_QUOTAS = {
    "funny": 14,
    "memes": 3,
    "showerthoughts": 2,
    "showthoughts": 1
}

# ---------------- SCORING ----------------

def score_trend(trend):
    title = trend["title"].lower()
    subreddit = trend["subreddit"].lower()

    disqualifiers = ["politic", "shooting", "murder", "death", "trump", "biden"]
    if any(w in title for w in disqualifiers):
        return "Low"

    good_subs = ["funny", "memes", "showerthoughts", "showthoughts", "dadjokes"]
    if subreddit not in good_subs:
        return "Medium"

    if len(title) > 100:
        return "Low"
    elif len(title) < 60:
        return "High"
    else:
        return "Medium"

# ---------------- PROMPT ----------------

def build_ai_prompt(trend):
    return f"""
You are a professional merch designer creating SELLABLE print-on-demand products.

Your goal is NOT to summarize the post.
Your goal is to extract the underlying joke or insight
and translate it into something someone would buy.

IMPORTANT:
- Recommend the BEST merch product for this idea
- Think like a Printify seller optimizing for conversion
- Must stand alone without Reddit context
- Think in terms of giftability, impulse-buy appeal, and readability

ORIGINAL TREND:
r/{trend['subreddit']} — "{trend['title']}"

STEP 1 — INTERPRET THE HUMOR
Explain briefly why people found this funny or relatable.

STEP 2 — PRIMARY MERCHANDISE SLOGAN
One short, clear, sellable slogan.

STEP 3 — ALTERNATES
3 alternate slogan options.

STEP 4 — CANVA DESIGN IDEAS
Provide 3 different design approaches:
- Minimal / Deadpan
- Bold / Visual Gag
- Cozy / Personality-driven

Each should include layout, font vibe, colors, and optional graphic.

STEP 5 — ETSY OPTIMIZED KEYWORDS
Provide 10–15 SEO-friendly keywords optimized for mug buyers.

STEP 6 — MERCH FIT (CRITICAL)

Decide which merch product this idea works BEST on by thinking about
HOW and WHERE a real person would use or display it.

Use buyer behavior to guide your choice:

• Mugs = personal identity, daily routine, gifts for someone else
• T-shirts / Hoodies = outward expression, worn publicly, social signaling
• Stickers = low-commitment humor, inside jokes, laptops/water bottles
• Posters = aesthetic or statement pieces for a room
• Tote bags = functional + visible, lifestyle alignment
• Hats = subtle identity signaling, repeat wear

Choose ONE primary product that would realistically convert best
for this specific idea.

Then list up to 3 secondary products that also make sense.

If a product clearly does NOT fit (wrong context, too private/public,
joke doesn’t translate, etc.), list it under "avoid".

IMPORTANT:
• Do NOT default to mugs
• Do NOT pick products just because they are popular
• Explain the *implicit reasoning* through your choices

STEP 7 — TREND SIGNALS (FOR TIER 2)

Evaluate this slogan/idea for REALISTIC online trend potential and merchability.

Use commercial standards similar to Etsy, Amazon Merch, and viral social media products.

IMPORTANT:
Do NOT default to "Medium." Use the full range.

High = strong evidence of demand, virality, or proven merch success
Medium = plausible but unproven or moderate appeal
Low = weak demand, niche interest, or unlikely to sell broadly

Return the following fields under "trend_signals":

1. merch_potential:
   Ability to sell as physical merchandise (shirts, mugs, stickers, etc.)
   Consider catchiness, relatability, visual design potential, giftability, and precedent.
2. hashtag_growth:
   Evidence of increasing usage on TikTok, Instagram, X, Reddit, etc.
   High only if likely to trend or currently trending.
3. memetic_variations:
   Whether the idea is reused, remixed, or adaptable into many jokes or formats.
4. cross_platform_spread:
   Presence across multiple platforms (not confined to a single community).
5. search_volume_mentions:
   Likelihood people are actively searching, discussing, or referencing it.
6. merch_branding:
   Evidence similar phrases or themes already succeed on merchandise.
7. rationale:
   3–5 sentences explaining your reasoning using concrete factors.
8. examples:
   Optional list of strong merch applications (mugs, shirts, stickers, etc.)
Be realistic, not optimistic. Assume this will compete in crowded online marketplaces.
Assume only ~20% of ideas deserve "High" ratings.

""".strip()


# ---------------- EMAIL ----------------

def send_email(subject, html_body, attachment_path=None):
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY not set")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    attachments = []

    if attachment_path:
        with open(attachment_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        attachments.append({
            "content": encoded,
            "name": os.path.basename(attachment_path)
        })

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": e} for e in TO_EMAILS],
        sender={"email": FROM_EMAIL, "name": "Daily Merch Bot"},
        subject=subject,
        html_content=html_body,
        attachment=attachments if attachments else None
    )

    api_instance.send_transac_email(email)

# For sending Tier 1 Emails
def send_tier1_email(date_str, email_body):
    send_email(
        subject=f"☕ Culture → Merch Ideas — {date_str}",
        html_body=email_body,
        attachment_path=None
    )

# For sending Tier 2 Emails
def send_tier2_email(date_str, email_body, pdf_path):
    send_email(
        subject=f"☕ Builder Edition — Merch Ideas — {date_str}",
        html_body=email_body,
        attachment_path=pdf_path
    )

def classify_trend_type(trend):
    """
    Classifies a trend into one of four strategy types:
    Reliable Seller, Momentum Play, Niche Opportunity, Creative Wildcard
    Uses ONLY existing signals (no AI call).
    """

    ai = trend.get("ai_enrichment", {}) or {}
    signals = ai.get("trend_signals", {}) or {}
    sniff = trend.get("tier2_sniff", {}) or {}

    merch = (signals.get("merch_potential") or "").lower()
    buzz = (signals.get("hashtag_growth") or "").lower()
    audience = (signals.get("cross_platform_spread") or "").lower()

    score = sniff.get("sniff_score", 0) or 0
    confidence = sniff.get("confidence", 0) or 0

    # ⭐ Proven Angle
    if (
        merch == "high"
        and audience == "high"
        and score >= 70
    ):
        return "Proven Angle"

    # 🔥 MOMENTUM PLAY
    if (
        buzz == "high"
        and score >= 60
        and confidence < 85
    ):
        return "Momentum Play"

    # 🎯 NICHE OPPORTUNITY
    if (
        merch in ["high", "medium"]
        and audience in ["low", "medium"]
        and score >= 60
    ):
        return "Niche Opportunity"

    # ⚡ FALLBACK
    return "Wildcard"

def group_trends(trends):
    grouped = {g: [] for g in GROUP_ORDER}

    for t in trends:
        group = t.get("group", "Wildcard")

        if group not in grouped:
            group = "Wildcard"

        grouped[group].append(t)

    return grouped


# ---------------- MAIN ----------------
def run():
    print("☕ Generating Daily Merch Ideas (Semi-AI MVP)…")

    # ----------------------------
    # Fetch Reddit Trends
    # ----------------------------
    trends = get_reddit_trends()
    if not trends:
        print("⚠️ No trends found.")
        return

    #google_trends_today = get_daily_trends()

    # ----------------------------
    # 1 Score viability FIRST
    # ----------------------------
    for t in trends:
        t["viability"] = score_trend(t)

    # ----------------------------
    # 2 Filter High / Medium
    # ----------------------------
    trends = [
        t for t in trends
        if t.get("viability") in ["High", "Medium"]
    ]

    # ----------------------------
    # 3 Sort by viability
    # ----------------------------
    trends.sort(
        key=lambda t: {"High": 1, "Medium": 2}[t["viability"]]
    )

    # ----------------------------
    # Sniff scoring helpers
    # ----------------------------
    def sniff_score(t):
        sniff = t.get("tier2_sniff") or {}
        return sniff.get("sniff_score", 0)

    # ----------------------------
    # 4 Run sniff tests on ALL viable trends
    # ----------------------------
    print(f"🧪 Running sniff tests on {len(trends)} candidates...")

    for trend in trends:
        trend["tier2_sniff"] = run_tier2_sniff(trend, client)

    # ----------------------------
    # 5 Filter weak commercial signals
    # ----------------------------
    trends = [
        t for t in trends
        if sniff_score(t) >= 40   # adjustable threshold
    ]

    if not trends:
        print("⚠️ No strong trends found after sniff filtering.")
        return

    # ----------------------------
    # 6 Rank by commercial strength
    # ----------------------------
    trends.sort(key=sniff_score, reverse=True)

    # ----------------------------
    # 7 Select TOP N trends
    # ----------------------------
    selected = trends[:TOP_N]

    print(f"📄 Final trends selected for email: {len(selected)}")


    # --------------------------------
    # AI ENRICHMENT: ON TRENDS THAT MEET A SNIFF SCORE OF >= 40
    # --------------------------------
    for idx, trend in enumerate(selected, 1):
        print(f"🧠 Enriching Trend {idx} with OpenAI...")

        prompt = build_ai_prompt(trend) + """
Please return your design suggestions as a JSON array of objects.
Each object must have these keys: style, layout, font_vibe, colors, graphic.
Example:
[
  {
    "style": "Minimal / Deadpan",
    "layout": "Centered text with a simple border",
    "font_vibe": "Sans-serif, modern",
    "colors": "Black text on white mug",
    "graphic": "None"
  }
]
"""
        ai_data = enrich_trend_with_ai(trend, prompt=prompt)

        trend["ai_enrichment"] = {
            "merch_angle": ai_data.get("merch_angle", ""),
            "slogan": ai_data.get("slogan", ""),
            "alternates": ai_data.get("alternates", []),
            "design": ai_data.get("design", []),
            "merch_fit": ai_data.get("merch_fit", {
                "primary": "",
                "secondary": [],
                "avoid": []
            }),
            "keywords": ai_data.get("keywords", []),
            "risks": ai_data.get("risks", ""),
            # <-- updated to match new prompt structure
            "trend_signals": ai_data.get("trend_signals", {
                "merch_potential": "",
                "hashtag_growth": "",
                "memetic_variations": "",
                "cross_platform_spread": "",
                "search_volume_mentions": "",
                "merch_branding": "",
                "rationale": "",
                "examples": []
            })
        }

        print(f"✅ AI enrichment attached to Trend {idx}")

    # Assign strategy group to each trend
    for t in selected:
        t["group"] = classify_trend_type(t)

    # Group selected trends into strategy categories
    trend_groups = group_trends(selected)
    
    #debug for groups
    for g, items in trend_groups.items():
        print(g, ":", len(items))

    # ----------------
    # Prepare output
    # ----------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    html_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.html")
    pdf_path = html_path.replace(".html", ".pdf")
    json_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.json")

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2, ensure_ascii=False)

    # Normalize trends for email (merge AI enrichment)
    email_trends = [
        normalize_trend_for_email(t)
        for t in selected
    ]

    # Generate AI-written Tier 1 email using normalized, enriched trends
    print("📬 Sending Tier 1 email (with NO attachment)…")
    email_body = generate_tier1_email(
        date_str=today,
        trends=email_trends
    )

    print("📬 Sending Tier 2 email (with attachment)…")
    tier2_email_body = generate_tier2_email(
        date_str=today,
        trends=email_trends,
        max_trends=4
    )

    # Safety check
    if len(email_body) < 300:
        raise ValueError("Tier 1 email body unexpectedly short")

    # Build HTML report to be converted to a PDF
    html_lines = [
        "<html><head><meta charset='UTF-8'><title>Merch Scout Daily Brief</title>",
        "<style>",

        "body { font-family: Arial, Helvetica, sans-serif; background: #fafafa; color: #222; padding: 40px; }",

        # Cover header
        ".cover { margin-bottom: 32px; }",
        ".brand { font-size: 34px; font-weight: 700; }",
        ".subtitle { color: #666; margin-top: 4px; }",
        ".meta { margin-top: 10px; font-size: 14px; color: #777; }",

        # Group Sections
        ".group { margin-top: 40px; }",
        ".group-title { font-size: 26px; margin-bottom: 6px; }",
        ".group-desc { color: #666; margin-bottom: 18px; }",
        ".empty-note { font-style: italic; color: #777; margin-bottom: 20px; }",

        # Trend Card
        ".trend { background: #ffffff; border-radius: 10px; padding: 24px; margin-bottom: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); page-break-inside: avoid; }",

        ".signals { background: #f7f7f7; border-radius: 6px; padding: 12px; margin: 12px 0; }",
        ".row { margin: 4px 0; font-size: 14px; }",
        ".label { font-weight: bold; }",

        ".keywords { background: #f6f6f6; padding: 12px; border-radius: 6px; font-size: 14px; }",

        ".design-block { background: #f9f9f9; border-left: 4px solid #ddd; padding: 12px; margin-bottom: 12px; }",

        ".badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }",
        ".badge-high { background: #e6f6ea; color: #1e7e34; }",
        ".badge-medium { background: #fff4e5; color: #a86b00; }",
        ".badge-low { background: #fdecea; color: #b42318; }",
        ".badge-neutral { background: #eee; color: #666; }",

        ".section { margin-top: 18px; padding-top: 10px; border-top: 1px solid #eee; }",

        "</style></head><body>",

        # ===== COVER =====
        "<div class='cover'>",
        "<div class='brand'>Merch Scout — Daily Trend Brief</div>",
        "<div class='subtitle'>Actionable merch opportunities filtered for commercial potential</div>",
        f"<div class='meta'>{today} • {len(selected)} curated ideas</div>",
        "</div>"
    ]

    # =========================
    # GROUPED REPORT BODY
    # =========================

    trend_counter = 1  # Global numbering across groups

    for group_name in GROUP_ORDER:

        trend_groups_list = trend_groups.get(group_name, [])

        html_lines.append("<div class='group'>")
        html_lines.append(f"<div class='group-title'>{group_name}</div>")

        # ---------- PLACEHOLDER ----------
        if not trend_groups_list:
            html_lines.append(
                f"<p class='empty-note'>{GROUP_PLACEHOLDER[group_name]}</p>"
            )
            html_lines.append("</div>")
            continue

        # ---------- EACH TREND ----------
        for t in trend_groups_list:

            html_lines.append("<div class='trend'>")
            html_lines.append(f"<h2>Trend {trend_counter}</h2>")

            trend_counter += 1

            if "ai_enrichment" in t:
                ai = t["ai_enrichment"]

                slogan = ai.get("slogan", "")
                alternates = ai.get("alternates", [])
                keywords = ", ".join(ai.get("keywords", []))

                signals = ai.get("trend_signals", {})
                sniff = t.get("tier2_sniff", {}) or {}

                # ---------- Design HTML ----------
                design_html = ""
                for d in ai.get("design", []):
                    if isinstance(d, dict):
                        design_html += "<div class='design-block'>"
                        design_html += f"<strong>{html.escape(d.get('style',''))}</strong><br>"
                        design_html += f"Layout: {html.escape(d.get('layout',''))}<br>"
                        design_html += f"Font vibe: {html.escape(d.get('font_vibe',''))}<br>"
                        design_html += f"Colors: {html.escape(d.get('colors',''))}<br>"
                        design_html += f"Graphic: {html.escape(d.get('graphic',''))}</div>"

                # ---------- Alternate slogans ----------
                alt_html = ""
                if alternates:
                    alt_html = "<ul style='margin: 0 0 12px 16px; font-size: 14px;'>"
                    for alt in alternates:
                        alt_html += f"<li>{html.escape(alt)}</li>"
                    alt_html += "</ul>"

                # ---------- Audience Size ----------
                aud_emoji, aud_label = format_audience_size(
                    signals.get("cross_platform_spread")
                )

                def pdf_score_badge(score):
                    try:
                        score = int(score)
                    except:
                        return "<span class='badge badge-neutral'>—</span>"

                    if score >= 75:
                        return f"<span class='badge badge-high'>{score}</span>"
                    elif score >= 50:
                        return f"<span class='badge badge-medium'>{score}</span>"
                    else:
                        return f"<span class='badge badge-low'>{score}</span>"

                def pdf_signal_badge(level):
                    level = (level or "").lower()

                    if level == "high":
                        return "<span class='badge badge-high'>High</span>"
                    elif level == "medium":
                        return "<span class='badge badge-medium'>Medium</span>"
                    elif level == "low":
                        return "<span class='badge badge-low'>Low</span>"
                    else:
                        return "<span class='badge badge-neutral'>—</span>"

                # ---------- CONTENT ----------
                html_lines.extend([

                    # PRIMARY SLOGAN
                    "<h3>Primary Slogan</h3>",
                    f"<p><strong>{html.escape(slogan)}</strong></p>",

                    # ALTERNATES
                    "<h3>Alternate Slogans</h3>",
                    alt_html if alt_html else "<p>—</p>",

                    # SIGNALS BLOCK
                    "<div class='signals'>",

                    f"<div class='row'><span class='label'>Easy to Put on Products:</span> {pdf_signal_badge(signals.get('merch_potential'))}</div>",
                    f"<div class='row'><span class='label'>Buzz Right Now:</span> {pdf_signal_badge(signals.get('hashtag_growth'))}</div>",
                    f"<div class='row'><span class='label'>Multiple Design Potential:</span> {pdf_signal_badge(signals.get('memetic_variations'))}</div>",
                    f"<div class='row'><span class='label'>Audience Size:</span> {pdf_signal_badge(signals.get('cross_platform_spread'))}</div>",

                    "<hr>",

                    f"<div class='row'><span class='label'>Chance of Selling:</span> {pdf_score_badge(sniff.get('sniff_score'))} / 100</div>",
                    f"<div class='row'><span class='label'>Worth Making Now?:</span> {pdf_signal_badge(normalize_level(sniff.get('verdict')))}</div>",
                    f"<div class='row'><span class='label'>Signal Strength:</span> {format_percent(sniff.get('confidence'))}</div>",

                    f"<div class='row'><span class='label'>Outlook:</span> {html.escape(outlook_interpretation(signals.get('sniff_score')))}</div>",

                    "</div>",

                    # MERCH ANGLE
                    "<div class='section'>",
                        "<h3>Why it Works</h3>",
                    "</div>",
                    f"<p>{html.escape(ai.get('merch_angle',''))}</p>",

                    # DESIGN IDEAS
                    "<div class='section'>",
                        "<h3>Design Ideas</h3>",
                    "</div>",
                    design_html,

                    # KEYWORDS
                    "<div class='section'>",
                        "<h3>Etsy Keywords</h3>",
                    "</div>",
                    f"<div class='keywords'>{html.escape(keywords)}</div>",

                    # RISKS
                    "<div class='section'>",
                        "<h3>Risks / Notes</h3>",
                    "</div>",
                    f"<p>{html.escape(ai.get('risks') or 'None identified')}</p>",
                ])

            else:
                html_lines.append("<p><em>AI enrichment coming soon…</em></p>")

            html_lines.append("</div>")  # end trend

        html_lines.append("</div>")  # end group

    html_lines.append("</body></html>")

    # Save HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))
    print(f"✅ HTML report created: {html_path}")

    # Create PDF
    import subprocess
    subprocess.run([
        "wkhtmltopdf",
        "--enable-local-file-access",
        html_path,
        pdf_path
    ], check=True)
    print(f"📄 PDF created: {pdf_path}")

    # Sending Tiered Emails
    print("📬 Sending Tier 1 email (no attachment)…")
    send_tier1_email(
        date_str=today,
        email_body=email_body
    )

    print("📬 Sending Tier 2 email (with attachment)…")
    send_tier2_email(
        date_str=today,
        email_body=tier2_email_body,
        pdf_path=pdf_path
    )


    print("📬 Tiered emails sent successfully!")


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    run()


