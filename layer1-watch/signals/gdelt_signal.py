"""
gdelt_signal.py — GDELT news risk signal for layer1-watch.

Uses the free GDELT 2.0 Document API (no API key required) to fetch recent
news articles mentioning each corridor, then derives a `news_sentiment` score.

How the score works
───────────────────
1. Volume score   — raw article count / GDELT_MAX_COUNT_FOR_100 × 100
                    (capped at 100).  More articles = more market attention.
2. Sentiment boost — fraction of titles containing negative-risk keywords,
                    multiplied by 50 (max 50-point boost).
3. Final score    = min(100, volume_score + sentiment_boost)

The sentiment_boost allows the score to climb faster when articles are
explicitly about attacks, blockades, seizures, etc., vs. general coverage.

Normalisation reference (approximate):
  10 articles → ~7     (routine monitoring)
  50 articles → ~33    (elevated attention)
  100 articles → ~67   (significant event)
  150 articles → 100   (severe crisis — capped)

GDELT DOC API docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from config import (
    CORRIDORS,
    GDELT_DOC_API,
    GDELT_MAX_COUNT_FOR_100,
    GDELT_MAX_RECORDS,
    GDELT_REQUEST_TIMEOUT,
    GDELT_TIMESPAN,
)

logger = logging.getLogger(__name__)

# Keywords that, when found in an article title, indicate genuine conflict/risk.
# Presence lifts the sentiment_boost component of the score.
NEGATIVE_KEYWORDS: list[str] = [
    "attack", "war", "conflict", "missile", "strike", "sanction",
    "threat", "tension", "escalation", "closure", "blockade", "seized",
    "seizure", "drone", "military", "naval", "detained", "hostage",
    "explosion", "bomb", "killed", "wounded", "warship", "frigate",
    "intercept", "confrontation", "retaliation", "provocation",
]


# ── Normalisation (also used by backtest.py) ─────────────────────────────────

def normalize_news_count(article_count: int, negative_pct: float = 0.0) -> float:
    """
    Convert raw GDELT article count + negative-title fraction to a 0–100 score.

    This function is imported by backtest.py so the same normalisation logic
    applies in both live and historical modes. In the backtest, negative_pct
    defaults to 0.0 (we only have headline counts, not individual titles).

    Args:
        article_count : number of articles returned by the GDELT DOC API
        negative_pct  : fraction of articles (0.0–1.0) with a negative keyword
                        in the title (0.0 in backtest mode)

    Returns:
        float score in [0, 100]
    """
    volume_score = min(100.0, article_count / GDELT_MAX_COUNT_FOR_100 * 100.0)
    sentiment_boost = min(50.0, negative_pct * 50.0)   # max +50 points
    return round(min(100.0, volume_score + sentiment_boost), 1)


# ── Live fetch ────────────────────────────────────────────────────────────────

def fetch_live(
    corridor: str,
    timespan: str = GDELT_TIMESPAN,
) -> tuple[Optional[float], list[dict]]:
    """
    Query GDELT DOC API for articles about *corridor* and return a risk score.

    Args:
        corridor : one of "hormuz", "red_sea", "iran_exports"
        timespan : GDELT timespan string, e.g. "1d" (default) or "6h"

    Returns:
        (score, evidence_list)
        score        — float 0–100, or None if the API call failed
        evidence_list — list of evidence dicts matching the schema structure
    """
    if corridor not in CORRIDORS:
        logger.error("Unknown corridor: %s", corridor)
        return None, []

    query = CORRIDORS[corridor]["gdelt_query"]
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": GDELT_MAX_RECORDS,
        "timespan": timespan,
        "format": "json",
        "sort": "ToneDesc",   # most negative articles first
    }

    try:
        resp = requests.get(GDELT_DOC_API, params=params, timeout=GDELT_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("GDELT API request failed for %s: %s", corridor, exc)
        return None, []
    except ValueError as exc:
        logger.warning("GDELT returned invalid JSON for %s: %s", corridor, exc)
        return None, []

    articles: list[dict] = data.get("articles") or []

    if not articles:
        logger.info("GDELT [%s]: 0 articles returned — scoring 0", corridor)
        return 0.0, []

    # Count how many titles contain at least one negative keyword
    neg_count = sum(
        1
        for a in articles
        if any(kw in (a.get("title") or "").lower() for kw in NEGATIVE_KEYWORDS)
    )
    negative_pct = neg_count / len(articles)
    score = normalize_news_count(len(articles), negative_pct)

    logger.info(
        "GDELT [%s]: %d articles, %d negative (%.0f%%), score=%.1f",
        corridor, len(articles), neg_count, negative_pct * 100, score,
    )

    # Build evidence from the top-5 most-negative articles (already sorted ToneDesc)
    evidence: list[dict] = []
    for article in articles[:5]:
        seendate = article.get("seendate", "")
        try:
            ts = (
                datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
            ts = datetime.now(timezone.utc).isoformat()

        evidence.append({
            "source": "GDELT",
            "summary": (article.get("title") or "No title")[:250],
            "url": article.get("url", ""),
            "timestamp": ts,
        })

    return score, evidence
