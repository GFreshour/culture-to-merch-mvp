import os
import html
import json
import base64
from datetime import datetime, timedelta

from trends_reddit import get_reddit_trends

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# ---------------- CONFIG ----------------

OUTPUT_DIR = "output"
TOP_N = 20

FROM_EMAIL = "gary_freshour@hotmail.com"
TO_EMAIL = "daniellefreshour@gmail.com"

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
You are a professional merch designer creating SELLABLE coffee mugs.

Your goal is NOT to summarize the post.
Your goal is to extract the underlying joke or insight
and translate it into something someone would buy.

IMPORTANT:
- Coffee mugs ONLY
- Must stand alone without Reddit context
- Think in terms of giftability, impulse-buy appeal, and readability

ORIGINAL TREND:
r/{trend['subreddit']} — "{trend['title']}"

STEP 1 — INTERPRET THE HUMOR
Explain briefly why people found this funny or relatable.

STEP 2 — PRIMARY MUG SLOGAN
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
""".strip()

# ---------------- EMAIL ----------------

def send_email(subject, html_body, attachment_path):
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY not set")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

    api_client = sib_api_v3_sdk.ApiClient(configuration)
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    with open(attachment_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": TO_EMAIL}],
        sender={"email": FROM_EMAIL, "name": "Daily Merch Bot"},
        subject=subject,
        html_content=html_body,
        attachment=[
            {
                "content": encoded,
                "name": os.path.basename(attachment_path)
            }
        ]
    )

    api_instance.send_transac_email(email)

# ---------------- MAIN ----------------

def run():
    print("☕ Generating Daily Merch Ideas (Semi-AI MVP)…")

    trends = get_reddit_trends()
    if not trends:
        print("⚠️ No trends found.")
        return

    for t in trends:
        t["viability"] = score_trend(t)

    trends = [t for t in trends if t["viability"] in ["High", "Medium"]]
    trends.sort(key=lambda t: {"High": 1, "Medium": 2}[t["viability"]])

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

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    html_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.html")
    json_path = os.path.join(OUTPUT_DIR, f"daily_merch_{today}.json")

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2, ensure_ascii=False)

    # Build HTML
    html_lines = [
        "<html><head><meta charset='UTF-8'><title>Daily Merch Ideas</title>",
        "<style>",
        "body{font-family:Arial;padding:20px}",
        ".trend{border-bottom:1px solid #ddd;margin-bottom:30px;padding-bottom:20px}",
        ".prompt{background:#f6f6f6;padding:15px;white-space:pre-wrap;border-radius:6px}",
        "</style></head><body>",
        f"<h1>☕ Daily Merch Ideas — {today}</h1>",
        f"<p>Top {len(selected)} High & Medium viability ideas</p>"
    ]

    for i, t in enumerate(selected, 1):
        prompt = build_ai_prompt(t)
        html_lines.extend([
            "<div class='trend'>",
            f"<h2>Trend {i}</h2>",
            f"<p><strong>Subreddit:</strong> r/{html.escape(t['subreddit'])}</p>",
            f"<p><strong>Original Post:</strong> {html.escape(t['title'])}</p>",
            "<h3>AI Prompt</h3>",
            f"<div class='prompt'>{html.escape(prompt)}</div>",
            "</div>"
        ])

    html_lines.append("</body></html>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print(f"✅ HTML report created: {html_path}")

    # Send email with attachment
    print("🚀 Sending email with attachment…")

    email_html = """
    <h2>Your Daily Merch Ideas Are Ready ☕</h2>
    <p>The full report is attached so you can open it on your phone or computer.</p>
    <p>Skim, star favorites, and we’ll refine from there.</p>
    """

    send_email(
        subject=f"☕ Daily Merch Ideas — {today}",
        html_body=email_html,
        attachment_path=html_path
    )

    print("📬 Email sent successfully with attachment!")

# ---------------- ENTRY ----------------

if __name__ == "__main__":
    run()
