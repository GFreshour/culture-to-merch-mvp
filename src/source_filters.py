# source_filters.py
#
# Shared quality filter for SEARCH-class sources (Pinterest, Google Trends).
#
# These sources trend toward discrete queries — sports fixtures, monthly
# greetings, celebrity names — rather than cultural aesthetics. This filter
# rejects the common junk patterns so the pipeline only sees trend-like
# phrases.
#
# Philosophy: aggressive. If in doubt, reject. A false positive (junk in
# the email) is worse than a false negative (a missed trend).

import re

# ---------- MONTHS AND GREETINGS ----------
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    # Spanish (Pinterest often returns these)
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

GREETING_PREFIXES = [
    "hello", "welcome", "hi", "hey", "good morning",
    "bienvenido", "bienvenida", "hola",
    "happy",  # e.g. "happy september", "happy new year"
]

# ---------- SPORTS FIXTURES ----------
# Match patterns like "springboks vs all blacks", "atlético tucumán - river plate",
# "yankees vs mets", "lakers - celtics"
SPORTS_SEPARATOR_RE = re.compile(
    r"\b(vs\.?|v\.?|versus)\b| - ",  # " vs ", " v ", " versus ", or " - "
    re.IGNORECASE,
)

# Common sports-team tokens that should disqualify a trend
SPORTS_TEAM_HINTS = [
    "springboks", "all blacks", "yankees", "mets", "lakers", "celtics",
    "la liga", "premier league", "mls", "nba", "nfl", "mlb", "nhl",
    "fifa", "uefa", "atlético", "river plate", "boca", "real madrid",
    "barcelona", "manchester", "chelsea", "arsenal", "liverpool",
    "wvu", "ms state", "ole miss", "alabama", "georgia", "texas a&m",
]

# ---------- EVENT/SCHEDULE PATTERNS ----------
# Date-like patterns: "september 2026", "09/12", "week 3", "day 5"
DATE_LIKE_RE = re.compile(
    r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b"     # 09/12 or 09/12/2026
    r"|\b\d{4}\b"                          # bare year
    r"|\bweek\s+\d+\b"
    r"|\bday\s+\d+\b",
    re.IGNORECASE,
)

# ---------- GENERIC SEARCH JUNK ----------
# Phrases that indicate the trend is a query, not a concept
QUERY_PREFIXES = [
    "how to", "what is", "when is", "where is", "why is",
    "who is", "which is", "how do", "how does", "how much",
    "near me", "open now", "hours",
]

# Single-token or very short trends with no merch angle
MIN_WORDS = 2
MAX_WORDS = 12


def _has_sports_separator(t: str) -> bool:
    return bool(SPORTS_SEPARATOR_RE.search(t))


def _has_sports_team(t: str) -> bool:
    return any(hint in t for hint in SPORTS_TEAM_HINTS)


def _is_month_or_greeting(t: str) -> bool:
    """
    Reject 'hello september', 'welcome september', 'bienvenido septiembre',
    'happy new year', etc. Also reject standalone month names.
    """
    words = t.lower().split()

    # Standalone month: "september"
    if len(words) == 1 and words[0] in MONTHS:
        return True

    # Greeting + month: "hello september", "bienvenido septiembre"
    if len(words) == 2:
        first, second = words
        if first in GREETING_PREFIXES and second in MONTHS:
            return True

    return False


def _looks_like_query(t: str) -> bool:
    return any(t.startswith(p) for p in QUERY_PREFIXES)


def _is_too_short_or_long(t: str) -> bool:
    wc = len(t.split())
    return wc < MIN_WORDS or wc > MAX_WORDS


def is_valid_search_trend(title: str):
    """
    Returns (is_valid: bool, reason: str).

    reason is a short human-readable string explaining the rejection
    (or "ok" if it passed). Used for logging so we can see what we're
    filtering out and tune over time.
    """
    if not title:
        return False, "empty"

    t = title.strip()
    tl = t.lower()

    if _is_too_short_or_long(t):
        return False, f"word count {len(t.split())} out of range"

    if _is_month_or_greeting(t):
        return False, "month/greeting"

    if _has_sports_separator(t):
        return False, "sports separator (vs / -)"

    if _has_sports_team(tl):
        return False, "sports team token"

    if DATE_LIKE_RE.search(t):
        return False, "date-like"

    if _looks_like_query(tl):
        return False, "search query phrasing"

    # Single proper-noun name: "billie jean king" style
    # Heuristic: every word capitalized, no lowercase connectors
    words = t.split()
    if len(words) >= 2 and all(w[0].isupper() for w in words if w):
        # Allow if it's more than 3 words — could be a band/title
        if len(words) <= 3:
            return False, "proper-noun name"

    return True, "ok"