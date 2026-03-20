import os
import subprocess

WKHTMLTOPDF_PATH = "/usr/local/bin/wkhtmltopdf"


def test_env():

    print("Checking environment variables...")

    required_vars = [
        "OPENAI_API_KEY",
        "BREVO_API_KEY",
        "BREVO_LIST_ID",
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    print("Checking wkhtmltopdf...")

    try:
        subprocess.run(
            [WKHTMLTOPDF_PATH, "--version"],
            check=True,
            capture_output=True
        )
    except Exception as e:
        raise RuntimeError(f"wkhtmltopdf check failed at {WKHTMLTOPDF_PATH}: {e}")

    print(" Environment OK")