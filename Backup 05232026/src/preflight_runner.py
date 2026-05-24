# src/preflight_runner.py
import sys
import traceback
from tests.test_env import test_env
from tests.test_scrapers import test_scrapers
from tests.test_ai_json import test_ai_json
from tests.test_email_generation import test_email_generation
from tests.test_pdf_engine import test_pdf_engine

def run_preflight():
    print(" Running Merch Scout preflight checks...\n")
    tests = [
        test_env,
        #test_scrapers,
        #test_ai_json,
        test_email_generation,
        test_pdf_engine
    ]

    failures = []

    for test in tests:
        try:
            test()
            print(f" {test.__name__} passed")
        except Exception as e:
            tb_str = "".join(traceback.format_exception_only(type(e), e)).strip()
            failures.append(f"{test.__name__} FAILED: {tb_str}")
            print(f" {test.__name__} FAILED")
            print(tb_str)
            print()

    if failures:
        summary = "\n".join(failures)
        print(f" Preflight failed with {len(failures)} error(s)")
        print(summary)
        sys.exit(1)
    else:
        print(" All preflight checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_preflight()