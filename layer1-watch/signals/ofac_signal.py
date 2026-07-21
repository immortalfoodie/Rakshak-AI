"""
ofac_signal.py — OFAC SDN sanctions-delta signal for layer1-watch.

Downloads the U.S. Treasury OFAC Specially Designated Nationals (SDN) list
CSV (public domain, no API key required, ~4 MB) and counts entries relevant
to each corridor's keywords.

How the score works
───────────────────
On first run: baseline count is stored in a local cache file and score = 0.
On subsequent runs: delta = current_count − cached_count is normalised:

  New entries | Score
  ──────────────────
       0      |   0
       1      |  25
       2      |  50
       3      |  70
       4      |  85
      ≥ 5     | 100

Rationale: OFAC typically issues targeted Iran/shipping designations 1–3 days
before media coverage reaches a crisis level, giving the combined model an
early-warning lead over naive keyword counting.

OFAC SDN CSV: https://www.treasury.gov/ofac/downloads/sdn.csv
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from layer1_config import (
    CORRIDORS,
    OFAC_CACHE_FILE,
    OFAC_REQUEST_TIMEOUT,
    OFAC_SDN_CSV_URL,
)

logger = logging.getLogger(__name__)

# Map cumulative new-entry count → normalised score
# Index = delta count (capped at 5)
_DELTA_SCORE_MAP: list[float] = [0.0, 25.0, 50.0, 70.0, 85.0, 100.0]


# ── Normalisation (also used by backtest.py) ─────────────────────────────────

def normalize_sanctions_delta(delta: int) -> float:
    """
    Map a count of new corridor-relevant OFAC SDN entries to a 0–100 score.

    Args:
        delta : number of new entries since last pipeline run (≥ 0)

    Returns:
        float score in [0, 100]
    """
    idx = min(max(0, delta), len(_DELTA_SCORE_MAP) - 1)
    return _DELTA_SCORE_MAP[idx]


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if OFAC_CACHE_FILE.exists():
        try:
            return json.loads(OFAC_CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("OFAC cache file corrupt — starting fresh")
    return {}


def _save_cache(data: dict) -> None:
    OFAC_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFAC_CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── SDN parsing ───────────────────────────────────────────────────────────────

_IN_MEMORY_CSV = None

def _download_sdn(url: str) -> Optional[str]:
    """Download OFAC SDN CSV text. Returns None on any network failure."""
    global _IN_MEMORY_CSV
    if _IN_MEMORY_CSV is not None:
        return _IN_MEMORY_CSV
        
    try:
        resp = requests.get(url, timeout=OFAC_REQUEST_TIMEOUT)
        resp.raise_for_status()
        _IN_MEMORY_CSV = resp.text
        return _IN_MEMORY_CSV
    except requests.RequestException as exc:
        logger.warning("OFAC SDN download failed: %s", exc)
        return None


def _count_corridor_entries(csv_text: str, keywords: list[str]) -> int:
    """
    Count CSV lines that contain at least one of the corridor keywords.

    Each row in the SDN CSV represents one designated entity. A line matches
    if any keyword appears anywhere in the row (name, program, remarks, etc.).
    """
    count = 0
    kw_upper = [kw.upper() for kw in keywords]
    for line in csv_text.splitlines():
        line_up = line.upper()
        if any(kw in line_up for kw in kw_upper):
            count += 1
    return count


# ── Live fetch ────────────────────────────────────────────────────────────────

def fetch_live(corridor: str) -> tuple[Optional[float], list[dict]]:
    """
    Download OFAC SDN, count corridor-relevant entries, compute delta vs cache.

    Args:
        corridor : one of "hormuz", "red_sea", "iran_exports"

    Returns:
        (score, evidence_list)
        score         — float 0–100, or None if download failed
        evidence_list — list of evidence dicts matching the schema structure
    """
    if corridor not in CORRIDORS:
        return None, []

    keywords = CORRIDORS[corridor]["ofac_keywords"]
    csv_text = _download_sdn(OFAC_SDN_CSV_URL)

    if csv_text is None:
        return None, []

    current_count = _count_corridor_entries(csv_text, keywords)
    cache = _load_cache()
    cache_key = f"ofac_{corridor}_count"
    now = datetime.now(timezone.utc).isoformat()

    if cache_key not in cache:
        # First run: establish baseline; no delta yet
        logger.info(
            "OFAC [%s]: First run — baseline count = %d", corridor, current_count
        )
        cache[cache_key] = current_count
        _save_cache(cache)
        delta = 0
    else:
        delta = max(0, current_count - cache[cache_key])
        logger.info(
            "OFAC [%s]: prev=%d, current=%d, delta=%d",
            corridor, cache[cache_key], current_count, delta,
        )
        cache[cache_key] = current_count
        _save_cache(cache)

    score = normalize_sanctions_delta(delta)

    # Build a single evidence item summarising the OFAC state
    if delta > 0:
        summary = (
            f"{delta} new SDN designation(s) added since last run for corridor "
            f"'{corridor}' (keywords: {', '.join(keywords[:3])}). "
            f"Total relevant entries now: {current_count}."
        )
    else:
        summary = (
            f"No new SDN entries detected for corridor '{corridor}'. "
            f"Total relevant entries: {current_count}."
        )

    evidence = [{
        "source": "OFAC",
        "summary": summary,
        "url": OFAC_SDN_CSV_URL,
        "timestamp": now,
    }]

    return score, evidence
