import os
import subprocess


def test_env():

    print("Checking environment variables...")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing")

    if not os.getenv("BREVO_API_KEY"):
        raise RuntimeError("BREVO_API_KEY missing")

    print("Checking wkhtmltopdf...")

    try:
        subprocess.run(["wkhtmltopdf", "--version"], check=True, capture_output=True)
    except Exception:
        raise RuntimeError("wkhtmltopdf not installed or not in PATH")

    print(" Environment OK")