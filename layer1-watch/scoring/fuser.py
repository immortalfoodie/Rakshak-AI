"""
fuser.py — Signal fusion engine for layer1-watch.

Combines available sub-scores into a single corridor risk score using
weighted averaging. Signals that are None (unavailable) have their weight
redistributed proportionally among whichever signals ARE available.

Weighting (when all three scored signals are present)
──────────────────────────────────────────────────────
  news_sentiment    40 %  — GDELT article volume + sentiment
  sanctions_delta   35 %  — OFAC SDN new-entry delta
  prediction_market 25 %  — Polymarket implied probability

  ais_dark_fleet   → always None  (no free AIS transponder-gap API)
  futures_spread   → always None  (no free real-time Brent/WTI futures API)

Weight redistribution example (prediction_market = None)
─────────────────────────────────────────────────────────
  available weight = 0.40 + 0.35 = 0.75
  news_sentiment  effective weight = 0.40 / 0.75 = 53.3 %
  sanctions_delta effective weight = 0.35 / 0.75 = 46.7 %

Alert thresholds
────────────────
  ≥ 75 → critical
  ≥ 55 → high
  ≥ 35 → medium
  <  35 → low
"""
from layer1_config import ALERT_THRESHOLDS, SIGNAL_WEIGHTS


def score_to_alert(score: float) -> str:
    """Convert a numeric score [0, 100] to an alert level string."""
    for threshold, level in ALERT_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def fuse(sub_scores: dict) -> tuple[float, str]:
    """
    Fuse sub-scores into an overall corridor risk score.

    Only signals listed in SIGNAL_WEIGHTS are considered; ais_dark_fleet and
    futures_spread are always skipped (they carry no weight).

    Args:
        sub_scores : dict matching the schema's sub_scores structure.
                     Values may be float or None.

    Returns:
        (overall_score, alert_level)
        overall_score — float rounded to 1 d.p., clamped to [0, 100]
        alert_level   — one of "low", "medium", "high", "critical"
    """
    # Filter to only scoreable, non-null signals
    available: dict[str, float] = {
        k: v
        for k, v in sub_scores.items()
        if v is not None and k in SIGNAL_WEIGHTS
    }

    if not available:
        return 0.0, "low"

    total_weight = sum(SIGNAL_WEIGHTS[k] for k in available)
    weighted_sum = sum(SIGNAL_WEIGHTS[k] * available[k] for k in available)

    score = round(weighted_sum / total_weight, 1)
    score = max(0.0, min(100.0, score))

    return score, score_to_alert(score)


def build_sub_scores(
    news_sentiment: "float | None",
    sanctions_delta: "float | None",
    prediction_market: "float | None",
) -> dict:
    """
    Assemble the sub_scores dict that exactly matches the schema structure.

    ais_dark_fleet and futures_spread are always None — they are set here
    explicitly so the output object is always schema-complete.

    Args:
        news_sentiment    : GDELT news score (0–100) or None
        sanctions_delta   : OFAC delta score (0–100) or None
        prediction_market : Polymarket score (0–100) or None

    Returns:
        dict with all five sub_scores keys.
    """
    return {
        "news_sentiment":    news_sentiment,
        "sanctions_delta":   sanctions_delta,
        "ais_dark_fleet":    None,    # No free AIS transponder-gap API
        "prediction_market": prediction_market,
        "futures_spread":    None,    # No free real-time Brent/WTI futures API
    }
