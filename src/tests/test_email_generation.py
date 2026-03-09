from ai_insights import generate_tier1_email, generate_tier2_email


def test_email_generation():

    print("Testing email generation...")

    sample = [{
        "merch_headline": "Mondays Need Coffee",
        "core_insight": "People relate to Monday struggle",
        "secondary_products": ["Mug", "T-Shirt"],
        "trend_signals": {}
    }]

    tier1 = generate_tier1_email("2026-01-01", sample)

    if len(tier1) < 200:
        raise RuntimeError("Tier1 email too short")

    tier2 = generate_tier2_email("2026-01-01", sample)

    if "<html>" not in tier2:
        raise RuntimeError("Tier2 email missing HTML")

    print(" Email generation OK")