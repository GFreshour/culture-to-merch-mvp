"""
Merch Scout Pipeline (v2)

Sources → Gate 0 → Sniff → Rank → Stratify
Top5 = Deep Strategic Execution
Watchlist = Light Monitoring Enrichment
Output = PDF + Tiered Email
"""
import os
import html
import json
import base64
from datetime import datetime, timedelta
from tier2_sniff import run_tier2_sniff
from trend_memory import dedupe_trends, remove_recent_trends

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
from utils import normalize_for_pdf, normalize_watchlist_for_pdf, extract_display_signals, normalize_hml

#from trends_reddit import get_reddit_trends
from trends_reddit_rss import get_reddit_trends_rss
from trends_x import get_x_trends
from trends_tiktok import get_tiktok_trends
from trends_substack import get_substack_trends

from tier0_product_gate import run_productability_gate

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from openai import OpenAI

client = OpenAI()

import json

#-----------------------
#-----Testing Stuff-----
#-----------------------
#Test for only generating 1 watchlist and 1 top 5 = True turns the test mode on.
TEST_MODE = False

TEST_ENV = True #Ensuring that emails don't go out to customers, and only me. True = testing emails

# --------------------------------
# -----RUNNING AUTOMATED TEST-----
# --------------------------------
# Minimal email function for preflight only
def send_email_simple(subject, html_body, to_emails=None):
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    import os, base64

    to_emails = to_emails or ["garyfreshour@gmail.com"]

    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        print(" BREVO_API_KEY not set, cannot send email")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": e} for e in to_emails],
        sender={"email": "gary_freshour@hotmail.com", "name": "Merch Scout Preflight"},
        subject=subject,
        html_content=html_body
    )

    try:
        api_instance.send_transac_email(email)
        print(f" Preflight email sent to {', '.join(to_emails)}")
    except ApiException as e:
        print(f" Failed to send preflight email: {e}")

import subprocess
import sys
import os

TEST_UNIT_RUN = True # Change to True to run full unit tests

if TEST_UNIT_RUN:
    print(" Running preflight checks via runner...")

    preflight_path = os.path.join(os.path.dirname(__file__), "preflight_runner.py")
    result = subprocess.run([sys.executable, preflight_path], capture_output=True, text=True)

    # Always print what the runner prints
    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        # Send failure email with the output from the runner
        send_email_simple(
            subject=" Merch Scout Preflight Failed",
            html_body=f"<p>Preflight checks failed:</p><pre>{result.stdout}</pre>"
        )
        sys.exit(1)  # stop program with proper exit code
    else:
        send_email_simple(
            subject=" Merch Scout Preflight Passed",
            html_body="<p>All preflight checks passed successfully.</p>"
        )
# ---------------- CONFIG ----------------

OUTPUT_DIR = "output"
TOP_N = 20

if TEST_ENV:
    print("🧪 TEST MODE — sending email to developer only")
    FROM_EMAIL = "gary_freshour@hotmail.com"
    TO_EMAILS = [
        "daniellefreshour@gmail.com",
        "garyfreshour@gmail.com",
        "serafinefreshour@gmail.com"
    ]
else:
    # Send to Brevo subscribers
    from utils import get_brevo_contacts
    FROM_EMAIL = "gary_freshour@hotmail.com"

    # Fetch all contacts
    contacts = get_brevo_contacts(list_id=12)
    
    # Filter helpers
    def get_contacts_for_tier(contacts, tier):
        return [
            c for c in contacts
            if c.get("TIER_LEVEL") == tier and c.get("SUB_STATUS") == "Active"
        ]
    
    tier1_contacts = get_contacts_for_tier(contacts, "Tier 1")
    tier2_contacts = get_contacts_for_tier(contacts, "Tier 2")

    #TO_EMAILS = get_brevo_contacts(list_id=12)  # Merch Scout Subscribers list ID

    # --- TEST PRINT & EXIT ---
    #print("🧪 TEST MODE — printing Brevo contacts from list 12")
    #print(f"📬 Total contacts fetched: {len(TO_EMAILS)}")
    #print("Sample emails:", TO_EMAILS[:10])  # first 10 for safety
    #print("✅ Brevo list test complete. Exiting without running main pipeline.")
    #import sys
    #sys.exit()  # stop execution before sending anything

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

def clean_text_for_prompt(text: str) -> str:
    """
    Cleans text so it is safe to inject into AI prompts.
    Prevents JSON-breaking characters.
    """
    if not text:
        return ""

    return (
        text.replace('"', "'")        # avoid breaking JSON quotes
            .replace("\n", " ")      # remove line breaks
            .replace("\r", " ")
            .strip()
    )

def build_ai_prompt(trend):
    """
    Builds the AI prompt for Top 5 Deep Strategic Execution enrichment.
    Returns strict JSON to populate the PDF/email.
    """
    clean_title = clean_text_for_prompt(trend['title'])

    return f"""
You are a senior merch strategist helping sellers create high-converting products.

Analyze this trend for **commercial execution**.
Do NOT summarize the post.
Extract the monetizable insight and build actionable strategy.
Be opinionated, decisive, and realistic about what will sell.

Trend:
r/{trend['subreddit']} — "{clean_title}"

Evaluate commercial potential based not only on current momentum, but also on niche variations, viral meme potential, and likely buyer engagement if executed well. Assign High, Medium, or Low honestly, considering realistic monetization opportunities, even if the trend isn’t yet widely saturated.
Consider how the trend would perform across multiple merch products and micro-niches, not just the main product idea.

Return STRICT JSON ONLY with this schema:

{{
  "merch_headline": "",
  "core_insight": "",
  "buyer_psychology": "",
  "target_audience": "",
  "primary_product": "",
  "secondary_products": [],
  "avoid_products": [],
  "design_direction": "",
  "niche_variations": [
    {{
      "niche_name": "",
      "subtext": "",
      "design_notes": "",
      "color_palette": "",
      "target_buyer": ""
    }}
  ],
  "differentiation_strategy": "",
  "risk_level": "",
  "execution_priority": "",
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

Instructions:

0. **merch_headline**
   - Create ONE short, punchy primary slogan.
   - 3–7 words max.
   - If the Reddit title is too long, compress it into something sellable.
   - Must work standalone on a shirt or mug.

1. **core_insight**
   - Explain why this trend resonates culturally.
   - Identify the human/emotional connection driving interest.

2. **buyer_psychology**
   - Identify the emotional trigger for purchase.
   - Examples: identity signaling, belonging, humor, nostalgia, irony, pride.

3. **target_audience**
   Be specific (age range, subculture, gifting buyer, etc.)

4. **primary_product**
   - ONE product most likely to convert immediately.

5. **secondary_products**
   - Up to 3 logical expansions that complement the primary product.

6. **avoid_products**
   - List products that would flop or feel forced.

7. **design_direction**
   - Concrete layout, typography, illustration style, composition, print placement.
   - Describe visual hierarchy, color choices, and imagery.

8. **niche_variations**
   Instead of random alternates, create 3 monetizable segmented versions.
   Each must include:
     - niche_name (e.g., "Best Friends Version")
     - subtext (optional line under headline)
     - design_notes (specific styling & placement)
     - color_palette (specific tones or vibe)
     - target_buyer (who this version is for)
    - Avoid generic alternates; each must feel Etsy-ready.

9. **differentiation_strategy**
   - How this version avoids copycats.
   - Include a unique angle, phrasing, or design feature.

10. **risk_level**
    - Low / Medium / High, with a short commercial justification.

11. **execution_priority**
    - Should this be tested immediately, batch tested, or monitored?

12. **trend_signals**
    - Assign realistic High / Medium / Low scores per category.
    - Categories:
      - merch_potential
      - hashtag_growth
      - memetic_variations
      - cross_platform_spread
      - search_volume_mentions
      - merch_branding
    - Provide rationale for each score.
    - Give real examples if relevant.
    - Avoid all Medium scores; be decisive.

Additional guidance:
- Be commercially sharp, tactical, and specific.
- Avoid vague, generic phrases or filler.
- If the trend is weak, state it clearly.
- Return JSON only — no commentary, no extra text.
""".strip()

# ---------------- PROMPT (Watchlist / Rapid Tier 2 Enrichment) ----------------
def build_watchlist_prompt(trend):
    """
    Builds the AI prompt for Watchlist / rapid Tier 2 enrichment.
    Returns strict JSON but with lighter detail than Top 5.
    """
    clean_title = clean_text_for_prompt(trend['title'])
    return f"""
You are a merch analyst providing a quick evaluation of a trend for potential print-on-demand products.

Trend:
r/{trend['subreddit']} — "{clean_title}"

Return STRICT JSON ONLY, using this schema:

{{
  "merch_headline": "",
  "core_insight": "",
  "primary_product": "",
  "secondary_products": [],
  "design_suggestion": "",
  "angle_variations": ["", ""],
  "risk_level": "",
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

Instructions:

1. **merch_headline**
   - Create ONE short, punchy slogan (3–7 words max).
   - Compress the Reddit title into a sellable hook.
   - Must work on a shirt, mug, or sticker.

2. **core_insight**
   - Briefly explain why this trend resonates.
   - Identify the human or emotional connection that drives interest.

3. **primary_product**
   - ONE product most likely to convert quickly.

4. **secondary_products**
   - Up to 2 logical complementary products.

5. **design_suggestion**
   - Short, actionable style/layout advice (2–3 sentences max).
   - Include colors, fonts, and imagery if relevant.

6. **angle_variations**
   - Provide 2 alternate slogans, angles, or spin-offs for merch.
   - Should feel distinct and monetizable.

7. **risk_level**
   - Low / Medium / High commercial risk, with a short justification.
   - Be realistic; don’t sugarcoat weak trends.

8. **trend_signals**
   - Assign realistic High / Medium / Low scores per category:
     - merch_potential, hashtag_growth, memetic_variations,
       cross_platform_spread, search_volume_mentions, merch_branding
   - Provide concise rationale for each score.
   - Include examples if applicable.
   - Avoid generic “all Medium” scores; be decisive.

Additional guidance:
- Keep it concise, tactical, and commercially actionable.
- Avoid vague phrases or filler.
- Return JSON only — no commentary or extra text.
""".strip()


def enrich_top5_with_ai(trend):
    prompt = build_ai_prompt(trend)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a senior merch strategist helping sellers create high-converting products."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    raw_text = response.choices[0].message.content.strip()

    # 🔥 STRIP CODE FENCES IF PRESENT
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    
    try:
        parsed = json.loads(raw_text)
        return parsed
    except json.JSONDecodeError:
        print("⚠️ Top5 AI response invalid JSON")
        print(raw_text)
        return {}

# ---------------- Email Client Setup ----------------
def send_email(subject, html_body, attachment_path=None, to_emails=None):

    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY not set")

    # Determine recipients
    if to_emails:
        recipients = to_emails
    else:
        recipients = TO_EMAILS

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
        to=[{"email": FROM_EMAIL}],
        bcc=[{"email": e} for e in recipients],
        sender={"email": FROM_EMAIL, "name": "Daily Merch Bot"},
        subject=subject,
        html_content=html_body,
        attachment=attachments if attachments else None
    )

    api_instance.send_transac_email(email)

def send_failure_email(error: Exception):
    """Send an alert email to the developer if the main pipeline fails."""
    from_email = "gary_freshour@hotmail.com"
    to_emails = ["garyfreshour@gmail.com", "gary_freshour@hotmail.com"]
    subject = "⚠️ Merch Scout Pipeline Failed"
    import traceback
    body = f"""
    <p>The Merch Scout pipeline failed to execute.</p>
    <p><strong>Error:</strong></p>
    <pre>{html.escape(str(error))}</pre>
    <p><strong>Traceback:</strong></p>
    <pre>{html.escape(traceback.format_exc())}</pre>
    """

    try:
        api_key = os.getenv("BREVO_API_KEY")
        if not api_key:
            print("⚠️ BREVO_API_KEY not set. Cannot send failure email.")
            return

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        api_client = sib_api_v3_sdk.ApiClient(configuration)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": e} for e in to_emails],
            sender={"email": from_email, "name": "Merch Scout Alert"},
            subject=subject,
            html_content=body
        )

        api_instance.send_transac_email(email)
        print("✅ Failure email sent successfully.")

    except Exception as e:
        print(f"❌ Failed to send failure email: {e}")

# For sending Tier 1 Emails
def send_tier1_email(to_email=None, date_str=None, email_body=None):

    recipients = to_email if to_email else TO_EMAILS

    send_email(
        to_emails=recipients,
        subject=f"☕ Culture → Merch Ideas — {date_str}",
        html_body=email_body
    )

# For sending Tier 2 Emails
def send_tier2_email(to_email=None, date_str=None, email_body=None, pdf_path=None):

    recipients = to_email if to_email else TO_EMAILS

    send_email(
        to_emails=recipients,
        subject=f"☕ Builder Edition — Merch Ideas — {date_str}",
        html_body=email_body,
        attachment_path=pdf_path
    )

# ---------------- MAIN ----------------
def run():
    print("☕ Generating Daily Merch Ideas (Semi-AI MVP)…")

    print("☕ Fetching trends from Reddit and TikTok…")
    #raw_reddit_trends = get_reddit_trends(client)
    
    try:
        raw_reddit_trends = get_reddit_trends_rss()
    except Exception as e:
        print(f"⚠️ Reddit RSS failed completely: {e}")
        raw_reddit_trends = []
    
    try:
        trends_tiktok = get_tiktok_trends()
    except Exception as e:
        print(f"⚠️ TikTok scraper failed completely: {e}")
        trends_tiktok = []
    
    #Get substrack trends
    substack_trends = get_substack_trends(client)
    print(f"📊 Substack trends fetched: {len(substack_trends)}")

    all_raw_trends = raw_reddit_trends + trends_tiktok + substack_trends
    
    #raw_x_trends = get_x_trends(client)

    # Combine both sources
    print(f"📊 Total raw trends before Gate 0: {len(all_raw_trends)}")

    print(f"📊 Raw trends collected: {len(all_raw_trends)}")

    # Dedup and ensure trends are not from the last report
    all_raw_trends = dedupe_trends(all_raw_trends)
    print(f"📊 After internal dedupe: {len(all_raw_trends)}")

    all_raw_trends = remove_recent_trends(all_raw_trends)
    print(f"📊 After history filter: {len(all_raw_trends)}")

    num_raw_trends = len(all_raw_trends)  # count of all trends for email

    # ----------------------------
    # Tier 0 — Productability Gate
    # ----------------------------
    print("🛡 Running Tier 0 Productability Gate on all trends…")
    gate_passed_trends = []
    for trend in all_raw_trends:
        gated = run_productability_gate(trend, client)
        if gated:
            gate_passed_trends.append(gated)

    print(f"✅ {len(gate_passed_trends)} trends passed Gate 0")

    # Use gate_passed_trends instead of old Reddit-only list
    trends = gate_passed_trends

    if not trends:
        print("⚠️ No trends passed Tier 0. Exiting run.")
        return

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
        return sniff.get("sniff_score", sniff.get("commercial_score", 0))

    # ----------------------------
    # 4 Run sniff tests on ALL viable trends
    # ----------------------------
    print(f"🧪 Running sniff tests on {len(trends)} candidates...")

    for trend in trends:
        trend["tier2_sniff"] = run_tier2_sniff(trend, client)
    
    print(f"📊 Trends after sniff test: {len(trends)}")
    # --------------------------------
    # NORMALIZE NUMERIC SCORES (FIXED SCALE)
    # --------------------------------
    for trend in trends:
        sniff = trend.get("tier2_sniff") or {}

        # ---- SCORE NORMALIZATION ----
        raw_score = (
            sniff.get("sniff_score")
            or sniff.get("commercial_score")
            or 0
        )

        try:
            raw_score = float(raw_score)
        except:
            raw_score = 0

        # Convert 0–10 scale → 0–100
        if raw_score <= 10:
            score = int(raw_score * 10)
        else:
            score = int(raw_score)

        trend["commercial_score"] = score

        # ---- CONFIDENCE NORMALIZATION ----
        raw_conf = (
            trend.get("confidence_level")
            or sniff.get("confidence_level")
            or 0
        )

        try:
            raw_conf = float(raw_conf)
        except:
            raw_conf = 0

        # Handle 0–1, 0–10, or 0–100
        if raw_conf <= 1:
            confidence = int(raw_conf * 100)
        elif raw_conf <= 10:
            confidence = int(raw_conf * 10)
        else:
            confidence = int(raw_conf)

        trend["confidence_level"] = confidence

    # ----------------------------
    # 5 Filter weak commercial signals
    # ----------------------------
    trends = [
        t for t in trends
        if t.get("commercial_score", 0) >= 40
    ]

    if not trends:
        print("⚠️ No strong trends found after sniff filtering.")
        return

    num_trends_qualified = len(trends)    # trends that made pdf and html

    # ----------------------------
    # 6 Rank by commercial strength (weighted)
    # ----------------------------
    def weighted_score(t):
        sniff = t.get("tier2_sniff") or {}

        commercial = t.get("commercial_score", 0)

        confidence = t.get("confidence_level", 0)

        audience_map = {"high": 100, "medium": 60, "low": 30}
        audience = audience_map.get(sniff.get("audience_size"), 60)

        return (
            commercial * 0.6 +     # stronger weight
            confidence * 0.3 +     # NEW: confidence matters
            audience * 0.1         # keep light
        )

    trends.sort(key=weighted_score, reverse=True)

    # ----------------------------
    # 7 Stratify into tiers
    # ----------------------------

    top5 = []
    watchlist = []

    # ⚡ TEST_MODE — only keep 1 result
    TEST_TOP5_LIMIT = 1 if TEST_MODE else 5
    TEST_WATCHLIST_LIMIT = 1 if TEST_MODE else 15


    # --------------------------------
    # AI ENRICHMENT — TOP 5 (DEEP BUILDER MODE)
    # --------------------------------

    print("🧠 Running Deep Enrichment on Top 5...")

    for trend in trends:

        if len(top5) >= TEST_TOP5_LIMIT:
            break

        print(f"🔥 Deep Enriching Top Trend {len(top5)+1}...")

        enrichment = enrich_top5_with_ai(trend)

        if not enrichment:
            print(f"⚠️ Skipping failed Top5 trend: {trend['title']}")
            continue

        trend["ai_enrichment"] = enrichment
        trend["report_tier"] = "Top 5"

        top5.append(trend)

        print(f"✅ Added to Top5: {trend['title']}")


    # --------------------------------
    # LIGHT ENRICHMENT — WATCHLIST
    # --------------------------------

    print("👀 Running Light Enrichment on Watchlist...")

    for trend in trends:

        # Skip anything already used in Top5
        if trend in top5:
            continue

        if len(watchlist) >= TEST_WATCHLIST_LIMIT:
            break

        idx = len(watchlist) + 1
        print(f"👀 Light Enriching Watchlist Trend {idx}...")

        light_prompt = build_watchlist_prompt(trend)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": light_prompt}],
                temperature=0.5
            )

            raw_text = response.choices[0].message.content.strip()

            # Strip code fences
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(raw_text)

        except Exception as e:
            print(f"⚠️ Watchlist enrichment failed for '{trend['title']}': {e}")
            continue

        trend["ai_enrichment"] = parsed
        trend["report_tier"] = "Watchlist"

        watchlist.append(trend)

        print(f"✅ Watchlist enrichment attached to: {trend['title']}")

    # --------------------------------
    # BACKFILL WATCHLIST IF TOO SMALL
    # --------------------------------

    WATCHLIST_TARGET = 15

    if len(watchlist) < WATCHLIST_TARGET:

        needed = WATCHLIST_TARGET - len(watchlist)

        print(f"⚠️ Watchlist short by {needed}. Backfilling...")

        used_titles = {t["title"] for t in top5 + watchlist}

        for trend in trends:

            if trend["title"] in used_titles:
                continue

            trend["report_tier"] = "Watchlist"
            watchlist.append(trend)

            print(f"➕ Backfilled: {trend['title']}")

            if len(watchlist) >= WATCHLIST_TARGET:
                break

    print(f"📊 Final watchlist size: {len(watchlist)}")
    #for trend in early:
    #    trend["report_tier"] = "Early Signal"

    # ----------------
    # Prepare output
    # ----------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    html_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.html")
    pdf_path = html_path.replace(".html", ".pdf")
    json_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.json")

    # Save JSON
    final_trends = top5 + watchlist # + early

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_trends, f, indent=2, ensure_ascii=False)

    # Normalize trends for email (merge AI enrichment)
    #email_trends = [
    #    normalize_trend_for_email(t)
    #    for t in top5
    #]

    print("📬 Sending Tier 1 email (with NO attachment)…")
    tier1_email_body = generate_tier1_email(
        date_str=today,
        trends=top5[:3],               # keep it consistent with Tier 2
        watchlist=watchlist[:2],       # optional watchlist teasers
        total_raw_trends=num_raw_trends,
        total_trends_qualified=num_trends_qualified
    )

    print("📬 Sending Tier 2 email (with attachment)…")
    tier2_email_body = generate_tier2_email(
        date_str=today,
        trends=top5[:3],
        watchlist=watchlist[:2],
        total_raw_trends=num_raw_trends,
        total_trends_qualified=num_trends_qualified,
    )

    # Safety check
    if len(tier1_email_body) < 300:
        raise ValueError("Tier 1 email body unexpectedly short")
    if len(tier2_email_body) < 300:
        raise ValueError("Tier 1 email body unexpectedly short")

    pdf_trends = [normalize_for_pdf(t) for t in top5]
    pdf_watchlist = [normalize_watchlist_for_pdf(t) for t in watchlist]

    print(f"PDF TOP 5 trends count: {len(pdf_trends)}")
    print(f"PDF Watchlist trends count: {len(pdf_watchlist)}")


    # =========================
    # Build HTML report to be converted to PDF
    # =========================
    html_lines = [
        "<html><head><meta charset='UTF-8'><title>Merch Scout Daily Brief</title>",
        "<style>",

        "body { font-family: Arial, Helvetica, sans-serif; background: #f4f6f8; color: #1f2933; padding: 40px; }",

        #/* Cover */
        ".cover { margin-bottom: 36px; }",
        ".brand { font-size: 34px; font-weight: 700; letter-spacing: -0.5px; color: #111827; }",
        ".subtitle { color: #6b7280; margin-top: 6px; font-size: 15px; }",
        ".meta { margin-top: 10px; font-size: 13px; color: #9ca3af; }",

        #/* Group Title */
        ".group-title { font-size: 18px; font-weight: 600; margin-bottom: 18px; color: #374151; }",

        #/* Trend Card */
        ".trend { background: #ffffff; border-radius: 12px; padding: 28px; margin-bottom: 32px; box-shadow: 0 6px 18px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; page-break-inside: avoid; }",

        ".trend h2 { margin-top: 0; margin-bottom: 10px; font-size: 22px; color: #111827; }",

        #/* Section Styling */
        ".section { margin-top: 22px; padding-top: 12px; border-top: 1px solid #eef2f7; }",
        ".section h3 { margin: 0 0 6px 0; font-size: 14px; letter-spacing: 0.5px; text-transform: uppercase; color: #4b5563; }",
        ".section p { margin: 0; font-size: 14px; line-height: 1.6; color: #374151; }",

        #/* Signals / Highlight Blocks */
        ".signals { background: #f9fafb; border-radius: 8px; padding: 14px; margin: 14px 0; border: 1px solid #eef2f7; }",

        #/* Niche Variations Card */
        ".niche-card { background: #f9fafb; border-radius: 10px; padding: 14px 16px; margin-bottom: 14px; border: 1px solid #e5e7eb; }",
        ".niche-card strong { font-size: 14px; color: #111827; }",
        ".niche-meta { font-size: 13px; color: #4b5563; margin-top: 4px; line-height: 1.5; }",

        #/* Badges */
        ".badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }",
        ".badge-high { background: #e6f4ea; color: #1e7e34; }",
        ".badge-medium { background: #fff7e6; color: #a86b00; }",
        ".badge-low { background: #fdecea; color: #b42318; }",
        ".badge-neutral { background: #f3f4f6; color: #6b7280; }",

        #/* Trend Signals */
        ".signals-table { width: 100%; margin: 18px 0 24px 0; border-collapse: collapse; text-align: center; table-layout: fixed; }",
        ".signals-table th { font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase; color: #666; padding-bottom: 6px; word-wrap: break-word;}",
        ".signals-table td { padding-top: 6px; width: 25%; }",

        #/* Section Banner (Unified Top 5 + Watchlist) */
        ".section-banner { padding: 28px 20px; margin: 50px 0 30px 0; text-align: center; border-radius: 6px; }",
        ".section-banner-title { font-size: 22px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }",
        ".section-banner-subtitle { font-size: 13px; opacity: 0.9; }",

        #/* Top 5 Section Styling */
        ".top-section { background-color: #1f4e79; color: white; }",

        #/* Watchlist Section Styling */
        ".watchlist-section { background-color: #e9eef4; color: #1f2d3d; }",

        #/* Optional: Slight visual softening for watchlist cards */
        ".watchlist-trend { border-left: 4px solid #ccc; }",

        "</style></head><body>",

        "<div class='cover'>",
        "<div class='brand'>Merch Scout — Daily Trend Brief</div>",
        "<div class='subtitle'>Actionable merch opportunities filtered for commercial potential</div>",
        f"<div class='meta'>{today} • {len(top5)} top trends, {len(watchlist)} watchlist items</div>",
        "</div>"
    ]

    def pdf_signal_badge(level):
        try:
            level = float(level)
        except:
            level = 0

        # Convert numeric confidence → label
        if level >= 80:
            label = "High"
            color = "#16a34a"  # green
        elif level >= 60:
            label = "Medium"
            color = "#f59e0b"  # amber
        else:
            label = "Low"
            color = "#dc2626"  # red

        return f"<span style='color:{color}; font-weight:600'>{label}</span>"

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

    trend_counter = 1

    def signal_badge(label):
        level = label.lower()

        if level == "high":
            cls = "badge-high"
        elif level == "medium":
            cls = "badge-medium"
        elif level == "low":
            cls = "badge-low"
        else:
            cls = "badge-neutral"

        return f"<span class='badge {cls}'>{label}</span>"

    # --------------------------
    # HEAVY ENRICHED TRENDS
    # --------------------------
    if top5:
        html_lines.append("""
            <div class="section-banner top-section">
                <div class="section-banner-title">Top 5 Strategic Execution</div>
                <div class="section-banner-subtitle">
                    Highest conviction. Deploy-ready merch opportunities.
                </div>
            </div>
            """)

        for t in pdf_trends:
            html_lines.append("<div class='trend'>")

            merch_headline = t.get("merch_headline", "")
            html_lines.append(f"<h2>{html.escape(merch_headline or f'Trend {trend_counter}')}</h2>")
            
            # Extracting the trend signals for Top 5
            signals = extract_display_signals(t)

            html_lines.append("<table class='signals-table'>")
            html_lines.append("<tr>")

            for label in signals.keys():
                html_lines.append(f"<th>{label}</th>")

            html_lines.append("</tr>")
            html_lines.append("<tr>")

            for value in signals.values():
                html_lines.append(f"<td>{signal_badge(value)}</td>")

            html_lines.append("</tr>")
            html_lines.append("</table>")

            trend_counter += 1

            # -----------------------------------
            # Pull Strategic Fields
            # -----------------------------------
            core = t.get("core_insight", "")
            psych = t.get("buyer_psychology", "")
            audience = t.get("target_audience", "")
            primary_product = t.get("primary_product", "")
            secondary = ", ".join(t.get("secondary_products", []))
            avoid = ", ".join(t.get("avoid_products", []))
            design = t.get("design_direction", "")
            niches = t.get("niche_variations", [])
            diff = t.get("differentiation_strategy", "")
            risk = t.get("risk_level", "")
            priority = t.get("execution_priority", "")

            # Gate 0
            sniff = t.get("tier2_sniff", {}) or {}
            sniff_reasoning = sniff.get("reasoning", {})

            # -----------------------------------
            # Niche Variations HTML
            # -----------------------------------
            niche_html = "<p>—</p>"
            if niches:
                niche_html = ""
                for n in niches:
                    niche_html += "<div class='niche-card'>"
                    niche_html += f"<strong>{html.escape(n.get('niche_name',''))}</strong><br>"

                    if n.get("subtext"):
                        niche_html += f"<div style='margin:4px 0; font-style:italic; color:#555;'>"
                        niche_html += html.escape(n.get("subtext"))
                        niche_html += "</div>"

                    niche_html += f"<div><strong>Design:</strong> {html.escape(n.get('design_notes',''))}</div>"
                    niche_html += f"<div><strong>Colors:</strong> {html.escape(n.get('color_palette',''))}</div>"
                    niche_html += f"<div><strong>Target:</strong> {html.escape(n.get('target_buyer',''))}</div>"
                    niche_html += "</div>"

            # -----------------------------------
            # Render Sections
            # -----------------------------------

            html_lines.extend([

                "<div class='section'><h3>Core Insight</h3></div>",
                f"<p>{html.escape(core or '—')}</p>",

                "<div class='section'><h3>Buyer Psychology</h3></div>",
                f"<p>{html.escape(psych or '—')}</p>",

                "<div class='section'><h3>Target Audience</h3></div>",
                f"<p>{html.escape(audience or '—')}</p>",

                "<div class='section'><h3>Primary Product</h3></div>",
                f"<p>{html.escape(primary_product or '—')}</p>",

                "<div class='section'><h3>Secondary Product Expansion</h3></div>",
                f"<p>{html.escape(secondary or '—')}</p>",

                "<div class='section'><h3>Avoid These Products</h3></div>",
                f"<p>{html.escape(avoid or '—')}</p>",

                "<div class='section'><h3>Design Direction</h3></div>",
                f"<p>{html.escape(design or '—')}</p>",

                "<div class='section'><h3>🎨 Niche-Specific Variations (Where the Money Is)</h3></div>",
                niche_html,

                "<div class='section'><h3>Differentiation Strategy</h3></div>",
                f"<p>{html.escape(diff or '—')}</p>",

                "<div class='section'><h3>Execution Priority</h3></div>",
                f"<p>{html.escape(priority or '—')}</p>",

                "<div class='section'><h3>Risk Level</h3></div>",
                f"<p>{html.escape(risk or 'Not specified')}</p>",

            ])

            html_lines.append("</div>")  # end trend

        html_lines.append("</div>")  # end group

    # --------------------------
    # LIGHT ENRICHED WATCHLIST
    # --------------------------
    if watchlist:

        html_lines.append("""
            <div class="section-banner watchlist-section">
                <div class="section-banner-title">Watchlist</div>
                <div class="section-banner-subtitle">
                    Early-stage signals. Monitor for breakout velocity.
                </div>
            </div>
            """)

        for idx, t in enumerate(pdf_watchlist, 1):
            html_lines.append("<div class='trend'>")

            merch_headline = t.get("merch_headline", "")
            html_lines.append(f"<h2>{html.escape(merch_headline or f'Watchlist {idx}')}</h2>")

            # Extracting the trend signals for watchlist
            signals = extract_display_signals(t)

            html_lines.append("<table class='signals-table'>")
            html_lines.append("<tr>")

            for label in signals.keys():
                html_lines.append(f"<th>{label}</th>")

            html_lines.append("</tr>")
            html_lines.append("<tr>")

            for value in signals.values():
                html_lines.append(f"<td>{signal_badge(value)}</td>")

            html_lines.append("</tr>")
            html_lines.append("</table>")

            html_lines.append("<p><strong>Core Insight:</strong> "
                f"{html.escape(t.get('core_insight','—'))}</p>")

            html_lines.append("<p><strong>Primary Product:</strong> "
                            f"{html.escape(t.get('primary_product','—'))}</p>")

            secondary = ", ".join(t.get("secondary_products", []))
            html_lines.append("<p><strong>Secondary Products:</strong> "
                            f"{html.escape(secondary or '—')}</p>")

            html_lines.append("<p><strong>Design Suggestion:</strong> "
                            f"{html.escape(t.get('design_suggestion','—'))}</p>")

            angle_variations = ", ".join(t.get("angle_variations", []))
            html_lines.append("<p><strong>Angle Variations:</strong> "
                            f"{html.escape(angle_variations or '—')}</p>")

            html_lines.append("<p><strong>Risk Level:</strong> "
                            f"{html.escape(t.get('risk_level','Not specified'))}</p>")

            html_lines.append("</div>")  # end trend

        html_lines.append("</div>")  # end watchlist group

    # --------------------------
    # FINISH HTML
    # --------------------------
    html_lines.append("</body></html>")

    # Save HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))
    print(f"✅ HTML report created: {html_path}")

    # Create PDF
    import subprocess
    subprocess.run([
        "/usr/local/bin/wkhtmltopdf",
        "--enable-local-file-access",
        html_path,
        pdf_path
    ], check=True)
    print(f"📄 PDF created: {pdf_path}")
    

    # Sending Tiered Emails
    if TEST_ENV:
        print("🧪 TEST MODE — sending both emails to developer")

        send_tier1_email(
            date_str=today,
            email_body=tier1_email_body
        )

        send_tier2_email(
            date_str=today,
            email_body=tier2_email_body,
            pdf_path=pdf_path
        )

    else:
        print("📬 Sending Tier 1 emails (no attachment)…")
        tier1_emails = [c["email"] for c in tier1_contacts]
        send_tier1_email(
            to_email=tier1_emails,
            date_str=today,
            email_body=tier1_email_body
        )

        print("📬 Sending Tier 2 emails (with attachment)…")
        tier2_emails = [c["email"] for c in tier2_contacts]
        send_tier2_email(
            to_email=tier2_emails,
            date_str=today,
            email_body=tier2_email_body,
            pdf_path=pdf_path
        )

    print("📬 Tiered emails sent successfully!")


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ Main pipeline failed: {e}")
        if not TEST_ENV:
            send_failure_email(e)
        raise  # keep the error in logs and exit with failure


