"""
config.py — Shared configuration for all layer1-watch signals and scoring.

All corridor definitions, API URLs, scoring weights, and alert thresholds
live here so every module stays in sync.
"""
from pathlib import Path

# ── Filesystem paths ─────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "layer1_output.schema.json"
MOCK_OUTPUT_PATH = REPO_ROOT / "shared" / "sample_data" / "mock_layer1_output.json"
OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent / "data"

# ── Corridor definitions ──────────────────────────────────────────────────────
CORRIDORS: dict[str, dict] = {
    "hormuz": {
        "name": "Strait of Hormuz",
        # GDELT DOC API query — targets crisis/conflict articles about this corridor
        "gdelt_query": 'Iran "Strait of Hormuz" OR "Persian Gulf" tanker oil threat conflict',
        # Keywords to match in OFAC SDN entries (case-insensitive)
        "ofac_keywords": ["IRAN", "IRGC", "ISLAMIC REVOLUTIONARY GUARD", "SEPAH"],
        # Polymarket market question search terms
        "polymarket_terms": ["Iran", "Hormuz", "Persian Gulf"],
        # Tickers to pull spread for
        "futures_tickers": ["CL=F", "BZ=F"],
        # Synthetic AIS dark fleet zone mapping
        "ais_zones": ["persian_gulf", "gulf_of_oman"]
    },
    "malacca": {
        "name": "Strait of Malacca",
        "gdelt_query": '"Strait of Malacca" OR "South China Sea" tanker piracy blockade',
        "ofac_keywords": ["CHINA", "PIRATE", "MALAYSIA", "INDONESIA"],
        "polymarket_terms": ["Malacca", "South China Sea"],
        "futures_tickers": ["CL=F", "BZ=F"],
        "ais_zones": ["malacca_strait"]
    },
    "suez": {
        "name": "Suez Canal",
        "gdelt_query": '"Suez Canal" OR "Red Sea" Houthi blockade attack tanker',
        "ofac_keywords": ["HOUTHI", "YEMEN", "EGYPT"],
        "polymarket_terms": ["Suez", "Red Sea", "Houthi"],
        "futures_tickers": ["CL=F", "BZ=F"],
        "ais_zones": ["red_sea", "suez"]
    },
    "red_sea": {
        "name": "Red Sea / Bab-el-Mandeb",
        "gdelt_query": '"Red Sea" Houthi tanker shipping attack OR Yemen conflict',
        "ofac_keywords": ["HOUTHI", "ANSARALLAH", "YEMEN", "IRAN"],
        "polymarket_terms": ["Red Sea", "Houthi", "Yemen"],
    },
    "iran_exports": {
        "name": "Iran Export Corridor",
        "gdelt_query": "Iran oil export sanction embargo crude petroleum",
        "ofac_keywords": ["IRAN", "PETROLEUM", "NAFTIRAN", "OIL"],
        "polymarket_terms": ["Iran", "oil", "sanction", "crude"],
    },
}

# ── Scoring weights ───────────────────────────────────────────────────────────
# Must sum to 1.0 when all three signals are available.
# ais_dark_fleet and futures_spread are always null — no free public APIs.
# When prediction_market is also null, weights are redistributed proportionally
# between news_sentiment (53.3%) and sanctions_delta (46.7%).
SIGNAL_WEIGHTS: dict[str, float] = {
    "news_sentiment": 0.40,
    "sanctions_delta": 0.35,
    "prediction_market": 0.25,
    # ais_dark_fleet  → always null, no free AIS transponder-gap API
    # futures_spread  → always null, no free real-time Brent/WTI futures API
}

# ── Alert thresholds ──────────────────────────────────────────────────────────
# Checked in order; first matching threshold wins.
ALERT_THRESHOLDS: list[tuple[float, str]] = [
    (75.0, "critical"),
    (55.0, "high"),
    (35.0, "medium"),
    (0.0,  "low"),
]

# Backtest: score must cross this value to count as "high alert"
HIGH_ALERT_THRESHOLD: float = 70.0

# ── GDELT DOC API ─────────────────────────────────────────────────────────────
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMESPAN = "1d"        # lookback window for live pipeline runs
GDELT_MAX_RECORDS = 250      # max articles per query (GDELT API cap)
GDELT_REQUEST_TIMEOUT = 5    # seconds (lowered from 30 to fail fast on rate limits)

# Max article count that maps to a news score of 100.
# 150 relevant articles in 24h = severe, sustained crisis coverage.
GDELT_MAX_COUNT_FOR_100 = 150.0

# ── OFAC SDN ─────────────────────────────────────────────────────────────────
OFAC_SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_REQUEST_TIMEOUT = 60    # SDN CSV is ~4 MB; give it time
OFAC_CACHE_FILE = DATA_DIR / ".ofac_cache.json"

# ── Polymarket ────────────────────────────────────────────────────────────────
POLYMARKET_API = "https://clob.polymarket.com/markets"
POLYMARKET_TIMEOUT = 10      # seconds; fail fast if API is slow
