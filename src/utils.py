import re

def clean_pdf_text(text: str) -> str:
    """
    Removes characters that break wkhtmltopdf, like invisible formatting
    marks, non-Latin CJK characters, or stray control codes.
    """
    if not isinstance(text, str):
        return text

    # 1. Remove zero-width spaces, directional marks, and BOMs
    text = re.sub(r'[\u200B-\u200D\u202A-\u202E\uFEFF]', '', text)
    
    # 2. Remove CJK (Chinese/Japanese/Korean) characters that sneak in
    # from hallucinations or bad encoding. Allow standard Latin-1, emojis,
    # and common punctuation.
    text = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uffef\u4e00-\u9faf\u3400-\u4dbf]', '', text)
    
    return text.strip()

def normalize_for_pdf(trend: dict) -> dict:
    ai = trend.get("ai_enrichment", {}) or {}

    # Clean the text fields that get rendered in the PDF
    headline = clean_pdf_text(ai.get("merch_headline", ""))
    source_context = clean_pdf_text(ai.get("source_context", ""))

    return {
        "title": clean_pdf_text(trend.get("title", "")),

        # NEW PRIMARY FIELD
        "merch_headline": headline,
        "source_context": source_context,

        # Strategic Fields
        "core_insight": clean_pdf_text(ai.get("core_insight", "")),
        "buyer_psychology": clean_pdf_text(ai.get("buyer_psychology", "")),
        "target_audience": clean_pdf_text(ai.get("target_audience", "")),
        "primary_product": clean_pdf_text(ai.get("primary_product", "")),
        "secondary_products": [clean_pdf_text(p) for p in ai.get("secondary_products", [])],
        "avoid_products": [clean_pdf_text(p) for p in ai.get("avoid_products", [])],
        "design_direction": clean_pdf_text(ai.get("design_direction", "")),

        # REPLACED FIELD
        "niche_variations": ai.get("niche_variations", []),

        "differentiation_strategy": clean_pdf_text(ai.get("differentiation_strategy", "")),
        "risk_level": clean_pdf_text(ai.get("risk_level", "")),
        "execution_priority": clean_pdf_text(ai.get("execution_priority", "")),
        "ai_artwork_prompt": clean_pdf_text(ai.get("ai_artwork_prompt", "")),
        "trend_signals": ai.get("trend_signals", {}),

        # Scoring Layer
        "commercial_score": trend.get("commercial_score", 0),
        "confidence_level": trend.get("confidence_level", 0)
    }

import json

def normalize_watchlist_for_pdf(trend: dict) -> dict:
    """
    Converts Watchlist AI enrichment into PDF-friendly fields.
    Lightweight version of normalize_for_pdf().
    """
    ai = trend.get("ai_enrichment", {}) or {}

    return {
        "title": trend.get("title", ""),
        "merch_headline": ai.get("merch_headline", ""),
        "core_insight": ai.get("core_insight", ""),
        "primary_product": ai.get("primary_product", ""),
        "secondary_products": ai.get("secondary_products", []),
        "design_suggestion": ai.get("design_suggestion", ""),
        "angle_variations": ai.get("angle_variations", []),
        "risk_level": ai.get("risk_level", ""),
        "trend_signals": ai.get("trend_signals", {})
}

def extract_display_signals(trend):
        signals = trend.get("trend_signals", {}) or {}

        momentum = normalize_hml(signals.get("hashtag_growth"))
        buyer_depth = normalize_hml(signals.get("merch_potential"))
        design_flex = normalize_hml(signals.get("memetic_variations"))
        monetization = normalize_hml(signals.get("search_volume_mentions"))

        return {
            "Momentum": momentum,
            "Buyer Depth": buyer_depth,
            "Design Flexibility": design_flex,
            "Monetization Potential": monetization
        }

def normalize_hml(value):
    """
    Converts a signal value into High/Medium/Low for display.

    Handles three input types:
      1. Numbers 0-100 (new format)
         - 0-30 → Low
         - 31-60 → Medium
         - 61-100 → High
      2. Strings containing keywords
         - "High - explanation" → High
         - "medium; because reasons" → Medium
      3. None or empty → Low
    """
    if value is None or value == "":
        return "Low"

    # Numeric path
    if isinstance(value, (int, float)):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "Low"
        if v >= 61:
            return "High"
        if v >= 31:
            return "Medium"
        return "Low"

    # String path — try to parse as a number first (JSON might give us "75")
    v_str = str(value).strip()
    try:
        v_num = float(v_str)
        if v_num >= 61:
            return "High"
        if v_num >= 31:
            return "Medium"
        return "Low"
    except ValueError:
        pass

    # Keyword path
    v = v_str.lower()
    if "high" in v or "strong" in v or "large" in v:
        return "High"
    if "medium" in v or "moderate" in v:
        return "Medium"
    if "low" in v or "small" in v or "weak" in v:
        return "Low"

    return "Medium"

import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def get_brevo_contacts(list_id: int):
    """
    Fetches all contacts from a specific Brevo list ID.
    Handles pagination to retrieve all contacts.
    Returns a list of dictionaries with email, TIER_LEVEL, and SUB_STATUS.
    """
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY not set")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    contacts_api = sib_api_v3_sdk.ContactsApi(api_client)

    all_contacts = []
    limit = 50
    offset = 0

    try:
        while True:
            response = contacts_api.get_contacts(limit=limit, offset=offset)
            
            # Filter for contacts in our list
            for c in response.contacts:
                if list_id in c.get("listIds", []):
                    contact_info = {
                        "email": c.get("email"),
                        "TIER_LEVEL": c.get("attributes", {}).get("TIER_LEVEL", "Tier 1"),  # default
                        "SUB_STATUS": c.get("attributes", {}).get("SUB_STATUS", "Inactive")   # default
                    }
                    all_contacts.append(contact_info)

            if len(response.contacts) < limit:
                break

            offset += limit

        print(f"✅ Total contacts fetched from list {list_id}: {len(all_contacts)}")
        return all_contacts

    except ApiException as e:
        print(f"❌ Failed to fetch contacts: {e}")
        return []

