"""
polymarket_signal.py — Polymarket prediction-market signal for layer1-watch.

Queries the Polymarket CLOB API (free, no authentication required) for open
prediction markets whose question text matches the corridor's search terms.

How the score works
───────────────────
• If a relevant market is found, the market's implied probability is mapped
  linearly to 0–100:  score = probability × 100
• Probabilities < 5% are treated as background noise and clipped to 0.
• If no relevant open market exists, returns (None, []).
  The fuser handles None by redistributing weight to other signals.

Polymarket CLOB API: https://clob.polymarket.com/markets

Note on historical backtesting
───────────────────────────────
No public Polymarket historical API exists. The prediction_market sub-score
is therefore always None in the backtest replays. In live operation it will
be populated when a relevant market is open.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from layer1_config import CORRIDORS, POLYMARKET_API, POLYMARKET_TIMEOUT

logger = logging.getLogger(__name__)


# ── Normalisation ─────────────────────────────────────────────────────────────

def probability_to_score(probability: float) -> float:
    """
    Map a Polymarket implied probability (0.0–1.0) to a 0–100 risk score.

    Args:
        probability : market best-bid price, representing implied probability

    Returns:
        float score in [0, 100]
    """
    if probability < 0.05:  # below 5% is baseline noise
        return 0.0
    return round(min(100.0, probability * 100.0), 1)


# ── Market matching ───────────────────────────────────────────────────────────

def _is_relevant(market: dict, search_terms: list[str]) -> bool:
    """Return True if the market text contains any of the corridor search terms."""
    text = " ".join([
        market.get("question", ""),
        market.get("description", ""),
        market.get("market_slug", ""),
    ]).lower()
    return any(term.lower() in text for term in search_terms)


def _extract_probability(market: dict) -> Optional[float]:
    """
    Extract the best available probability estimate from a Polymarket market dict.
    Tries fields in order of reliability.
    """
    for field in ("bestBid", "lastTradePrice", "bestAsk"):
        raw = market.get(field)
        if raw is not None:
            try:
                val = float(raw)
                if 0.0 <= val <= 1.0:
                    return val
            except (TypeError, ValueError):
                continue
    return None


# ── Live fetch ────────────────────────────────────────────────────────────────

def fetch_live(corridor: str) -> tuple[Optional[float], list[dict]]:
    """
    Search Polymarket for a relevant open market and return a risk score.

    Args:
        corridor : one of "hormuz", "red_sea", "iran_exports"

    Returns:
        (score, evidence_list)
        score         — float 0–100, or None if no relevant market found / API failed
        evidence_list — list of evidence dicts (empty if score is None)
    """
    if corridor not in CORRIDORS:
        return None, []

    search_terms = CORRIDORS[corridor]["polymarket_terms"]

    try:
        resp = requests.get(
            POLYMARKET_API,
            params={"closed": "false", "limit": 100},
            timeout=POLYMARKET_TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as exc:
        logger.warning("Polymarket API failed: %s", exc)
        return None, []
    except ValueError:
        logger.warning("Polymarket API returned non-JSON response")
        return None, []

    # API may return a list directly or a paginated object
    markets: list[dict] = raw if isinstance(raw, list) else raw.get("data", [])

    relevant = [m for m in markets if _is_relevant(m, search_terms)]

    if not relevant:
        logger.info("Polymarket [%s]: no relevant open markets found", corridor)
        return None, []

    # Pick the highest-probability market as the primary risk signal
    best_market: Optional[dict] = None
    best_prob: float = -1.0

    for market in relevant:
        prob = _extract_probability(market)
        if prob is not None and prob > best_prob:
            best_prob = prob
            best_market = market

    if best_market is None:
        logger.info("Polymarket [%s]: found %d markets but no valid price", corridor, len(relevant))
        return None, []

    score = probability_to_score(best_prob)
    now = datetime.now(timezone.utc).isoformat()

    slug = best_market.get("market_slug", "")
    question = best_market.get("question", "Unknown market")
    volume = best_market.get("volume", "N/A")

    logger.info(
        "Polymarket [%s]: '%s' prob=%.1f%% score=%.1f volume=$%s",
        corridor, question[:60], best_prob * 100, score, volume,
    )

    evidence = [{
        "source": "Polymarket",
        "summary": (
            f"Market: '{question}' — implied probability: {best_prob:.1%}. "
            f"Trading volume: ${volume}."
        ),
        "url": f"https://polymarket.com/event/{slug}",
        "timestamp": now,
    }]

    return score, evidence
