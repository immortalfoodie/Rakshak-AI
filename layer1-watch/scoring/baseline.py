"""
baseline.py — Naive keyword-count baseline model for layer1-watch backtests.

This is the "straw man" model. It simply counts how many times a set of
risk-related keywords appear in news article titles per day. When the daily
count exceeds BASELINE_THRESHOLD, the model fires a "high" alert.

Why include this?
─────────────────
Any serious risk model should outperform a trivial word-count heuristic.
By comparing the weighted multi-signal model against this baseline in the
backtest, we can quantify the improvement (in hours of advance warning) that
the OFAC sanctions signal and weighted fusion actually deliver.

Backtest threshold used: ≥ 100 keyword mentions/day → "high alert"
(chosen to match the frequency at which major crisis events are broadly covered
in English-language media, based on calibration to the historical test events).
"""

# Keywords to count in article title text.
# This set is broad enough to catch most geopolitical energy-risk events.
RISK_KEYWORDS: list[str] = [
    "iran", "attack", "sanction", "hormuz", "tanker",
    "houthi", "conflict", "military", "strike", "blockade",
    "seized", "threat", "escalation", "naval", "missile", "drone",
]

# Raw keyword mentions per day above this value → "high" alert
BASELINE_THRESHOLD: int = 100


def count_keywords(text: str) -> int:
    """
    Count total occurrences of all RISK_KEYWORDS in *text*.

    Args:
        text : concatenated news article titles (one per line, or space-separated)

    Returns:
        Total keyword mention count (a keyword appearing 3 times = 3 counts)
    """
    text_lower = text.lower()
    return sum(text_lower.count(kw) for kw in RISK_KEYWORDS)


def baseline_score(keyword_count: int) -> float:
    """
    Normalise a raw keyword count to a 0–100 score for comparison plots.

    Ceiling at 200 keyword mentions = score 100.
    """
    return round(min(100.0, keyword_count / 2.0), 1)


def baseline_alert(keyword_count: int) -> str:
    """
    Return "high" if keyword_count ≥ BASELINE_THRESHOLD, otherwise "low".

    The binary high/low mirrors the model's single threshold check in the
    backtest lead-time calculation.
    """
    return "high" if keyword_count >= BASELINE_THRESHOLD else "low"
