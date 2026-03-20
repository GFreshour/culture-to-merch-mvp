import subprocess
import tempfile

WKHTMLTOPDF_PATH = "/usr/local/bin/wkhtmltopdf"

def test_pdf_engine():

    print("Testing PDF generation...")

    html = "<html><body><h1>Test</h1></body></html>"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
        f.write(html.encode())
        html_path = f.name

    pdf_path = html_path.replace(".html", ".pdf")

    subprocess.run(
        [WKHTMLTOPDF_PATH, "--enable-local-file-access", html_path, pdf_path],
        check=True
    )

    print(" PDF engine OK")