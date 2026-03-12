import os
from sib_api_v3_sdk import Configuration, ApiClient
from sib_api_v3_sdk.api.transactional_emails_api import TransactionalEmailsApi
from sib_api_v3_sdk.models.send_smtp_email import SendSmtpEmail


def send_daily_email(html_file_path, report_date, to_email):
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY environment variable not set")

    # Load HTML content
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Add a friendly wrapper
    email_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>☕ Daily Mug Ideas — {report_date}</h2>
        <p>
            Here are today’s best coffee mug ideas based on what’s trending online.
            These are pre-filtered for humor, clarity, and mug viability.
        </p>

        <p>
            👉 <strong>Tip:</strong> Open this email on a computer for best readability.
        </p>

        <hr />

        {html_content}

        <hr />
        <p style="font-size: 12px; color: #777;">
            Generated automatically — MVP edition 💛
        </p>
    </body>
    </html>
    """

    config = Configuration()
    config.api_key["api-key"] = api_key

    with ApiClient(config) as api_client:
        api_instance = TransactionalEmailsApi(api_client)

        email = SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": os.getenv("BREVO_SENDER_EMAIL", to_email), "name": "Daily Mug Ideas"},
            subject=f"☕ Daily Mug Ideas — {report_date}",
            html_content=email_html
        )

        api_instance.send_transac_email(email)
