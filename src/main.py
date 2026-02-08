import os
import html
import json
import base64
from datetime import datetime, timedelta
from trends_google import get_daily_trends, google_trend_signal



# analyze_trend is a legacy / future helper (not used in run())
from ai_insights import generate_tier1_email, generate_tier2_email, analyze_trend

from trends_reddit import get_reddit_trends

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
        "why_it_works": merch_angle,
        "merch_ideas": merch_ideas[:3],
        "avoid": avoid,

        # 🔥 THIS IS THE FIX 🔥
        "trend_signals": signals,
        "rationale": signals.get("rationale", "")
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

Evaluate this slogan/idea for online trend potential and merchability.  
Return the following fields under "trend_signals":

1. merch_potential: High / Medium / Low (catchiness, relatability, visual adaptability, meme potential, precedent)
2. hashtag_growth: High / Medium / Low (usage on TikTok, Instagram, X, Reddit)
3. memetic_variations: High / Medium / Low (used in memes, captions, viral content)
4. cross_platform_spread: High / Medium / Low (present across multiple social platforms)
5. search_volume_mentions: High / Medium / Low (discussions, blogs, Reddit threads)
6. merch_branding: High / Medium / Low (already merchandised, branded campaigns)
7. rationale: 3–5 sentence explanation for your evaluations
8. examples: optional list of merch applications (mugs, shirts, stickers, etc.)


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


# ---------------- MAIN ----------------
def run():
    print("☕ Generating Daily Merch Ideas (Semi-AI MVP)…")


    trends = get_reddit_trends()
    if not trends:
        print("⚠️ No trends found.")
        return

    google_trends_today = get_daily_trends()
    #print("Google Trends today:", google_trends_today)

    # Score trends
    for t in trends:
        t["viability"] = score_trend(t)

    # Filter high/medium viability and sort
    trends = [t for t in trends if t["viability"] in ["High", "Medium"]]
    trends.sort(key=lambda t: {"High": 1, "Medium": 2}[t["viability"]])

    # Apply subreddit quotas
    quota_counts = {k: 0 for k in SUBREDDIT_QUOTAS}
    selected = []
    for t in trends:
        sub = t["subreddit"].lower()
        if sub in SUBREDDIT_QUOTAS:
            if quota_counts[sub] < SUBREDDIT_QUOTAS[sub]:
                selected.append(t)
                quota_counts[sub] += 1
        else:
            selected.append(t)

        if len(selected) >= TOP_N:
            break

    # --------------------------------
    # AI ENRICHMENT: MULTIPLE TRENDS
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
        # Debug print
        ts = trend["ai_enrichment"].get("trend_signals", {})

        print("📈 Trend Signals Debug")
        print("  Merch potential:", ts.get("merch_potential"))
        print("  Hashtag growth:", ts.get("hashtag_growth"))
        print("  Memetic variations:", ts.get("memetic_variations"))
        print("  Cross-platform spread:", ts.get("cross_platform_spread"))
        print("  Search volume / mentions:", ts.get("search_volume_mentions"))
        print("  Merch branding:", ts.get("merch_branding"))
        print("  Rationale:", ts.get("rationale"))
        print("  Examples:", ts.get("examples"))
        print("-" * 50)

        import pprint
        pprint.pprint(trends[0])


        #For Debuging
        #print("AI enrichment keys:", trend.get("ai_enrichment", {}).keys())
        #print("MERCH FIT:", trend["ai_enrichment"].get("merch_fit"))

        print(f"✅ AI enrichment attached to Trend {idx}")

    # --------------------------------
    # GOOGLE TRENDS SIGNAL (Step B)
    # --------------------------------
    #for trend in selected:
    #    trend["google_trends"] = google_trend_signal(
    #        trend.get("title", ""),
    #        google_trends_today
    #    )
    
    #Test the Google Trends
    #gt = trend.get("google_trends", {})
    #print(
    #    "📈 Google Trend Check:",
    #    f"title='{trend.get('title','')[:60]}…'",
    #    "| status =", gt.get("status", "MISSING")
    #)

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
    
    # 🔍 DEBUG — safe to remove later
    if email_trends:
        print("EMAIL TREND KEYS:", email_trends[0].keys())
        print("EMAIL SIGNALS:", email_trends[0].get("trend_signals"))

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

    # Build HTML report
    # (Everything here unchanged from your working version)
    html_lines = [
        "<html><head><meta charset='UTF-8'><title>Daily Merch Ideas</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; background: #fafafa; color: #222; padding: 40px; }",
        "h1 { font-size: 32px; margin-bottom: 10px; }",
        "h2 { font-size: 24px; margin-bottom: 5px; }",
        "h3 { margin-top: 24px; margin-bottom: 6px; }",
        "p { line-height: 1.5; }",
        ".trend { background: #ffffff; border-radius: 10px; padding: 24px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }",
        ".badge { display: inline-block; background: #eee; padding: 4px 10px; border-radius: 999px; font-size: 12px; margin-right: 8px; }",
        ".keywords { background: #f6f6f6; padding: 12px; border-radius: 6px; font-size: 14px; }",
        ".design-block { background: #f9f9f9; border-left: 4px solid #ddd; padding: 12px; margin-bottom: 12px; }",
        "</style></head><body>",
        f"<h1>☕ Daily Merch Ideas — {today}</h1>",
        f"<p>Top {len(selected)} High & Medium viability ideas</p>"
    ]

    for i, t in enumerate(selected, 1):
        html_lines.append("<div class='trend'>")
        html_lines.append(f"<h2>Trend {i}</h2>")
        html_lines.append(f"<p><strong>Subreddit:</strong> r/{html.escape(t['subreddit'])}</p>")
        html_lines.append(f"<p><strong>Original Post:</strong> {html.escape(t['title'])}</p>")

        if "ai_enrichment" in t:
            ai = t["ai_enrichment"]
            design_html = ""
            for d in ai.get("design", []):
                if isinstance(d, dict):
                    design_html += "<div class='design-block'>"
                    design_html += f"<strong>{html.escape(d.get('style',''))}</strong><br>"
                    design_html += f"Layout: {html.escape(d.get('layout',''))}<br>"
                    design_html += f"Font vibe: {html.escape(d.get('font_vibe',''))}<br>"
                    design_html += f"Colors: {html.escape(d.get('colors',''))}<br>"
                    design_html += f"Graphic: {html.escape(d.get('graphic',''))}</div>"
                else:
                    design_html += f"{html.escape(str(d))}<br>"

            keywords = ", ".join(ai.get("keywords", []))

            html_lines.extend([
                "<h3>🧠 Merch Angle</h3>",
                f"<p>{html.escape(ai.get('merch_angle',''))}</p>",
                "<h3>☕ Mug Slogan</h3>",
                f"<p><strong>{html.escape(ai.get('slogan',''))}</strong></p>",
                "<h3>🎨 Design Ideas</h3>",
                f"<p>{design_html}</p>",
                "<h3>🏷️ Etsy Keywords</h3>",
                f"<div class='keywords'>{html.escape(keywords)}</div>",
                "<h3>⚠️ Risks / Notes</h3>",
                f"<p>{html.escape(ai.get('risks',''))}</p>"
            ])
        else:
            html_lines.append("<p><em>AI enrichment coming soon…</em></p>")

        html_lines.append("</div>")

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


    # Send Tier 1 email with attachment
    #send_email(
    #    subject=f"☕ Fresh Culture → Merch Ideas — {today}",
    #    html_body=email_body,
    #    attachment_path=pdf_path
    #)
    print("📬 Tiered emails sent successfully!")


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    run()


