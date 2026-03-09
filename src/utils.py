def normalize_for_pdf(trend: dict) -> dict:
    ai = trend.get("ai_enrichment", {}) or {}

    return {
        "title": trend.get("title", ""),

        # NEW PRIMARY FIELD
        "merch_headline": ai.get("merch_headline", ""),

        # Strategic Fields
        "core_insight": ai.get("core_insight", ""),
        "buyer_psychology": ai.get("buyer_psychology", ""),
        "target_audience": ai.get("target_audience", ""),
        "primary_product": ai.get("primary_product", ""),
        "secondary_products": ai.get("secondary_products", []),
        "avoid_products": ai.get("avoid_products", []),
        "design_direction": ai.get("design_direction", ""),

        # REPLACED FIELD
        "niche_variations": ai.get("niche_variations", []),

        "differentiation_strategy": ai.get("differentiation_strategy", ""),
        "risk_level": ai.get("risk_level", ""),
        "execution_priority": ai.get("execution_priority", ""),
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
        if not value:
            return "Low"

        v = str(value).strip().lower()

        if v in ["high", "strong", "large"]:
            return "High"
        elif v in ["medium", "moderate"]:
            return "Medium"
        elif v in ["low", "small", "weak"]:
            return "Low"

        return "Medium"