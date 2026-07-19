"""
config.py — Central configuration for the Layer 2 economic impact model.

Every number in this file is a model parameter. They are grouped by the
step of the causal chain they belong to. Each parameter has a comment
explaining what it means and where the number comes from.

To tune the model, change values here — no other file needs editing.
"""

# ─────────────────────────────────────────────
# 1. CORRIDOR → SUPPLY DISRUPTION
# ─────────────────────────────────────────────

# Maps a corridor name to the share of *global* oil supply that
# transits through it (as a fraction, e.g. 0.20 = 20%).
# Source: EIA, "World Oil Transit Chokepoints" (2023).
CORRIDOR_GLOBAL_SHARE = {
    "hormuz": 0.20,       # ~20 mbpd through Hormuz out of ~100 mbpd global
    "red_sea": 0.12,      # ~12 mbpd through Bab el-Mandeb / Suez
    "iran_exports": 0.03, # Iran's own exports ~3 mbpd
}

# How much of *India's* crude imports come through each corridor.
# Source: PIB / Ministry of Petroleum (July 2026) — India now sources
# ~70% outside Hormuz, so ~30% still transits Hormuz. Earlier estimates
# were 40-45% but diversification has reduced this.
CORRIDOR_INDIA_SHARE = {
    "hormuz": 0.30,
    "red_sea": 0.10,
    "iran_exports": 0.04,
}

# India's crude oil import dependency (fraction).
# Source: PPAC "Snapshot of India's Oil & Gas Data" FY 2025-26.
INDIA_IMPORT_DEPENDENCY = 0.887  # 88.7%


# ─────────────────────────────────────────────
# 2. RISK SCORE → DISRUPTION SEVERITY
# ─────────────────────────────────────────────

# The Layer 1 risk score (0–100) is mapped to a "disruption fraction",
# i.e. how much of the corridor's flow is assumed to be cut.
# This is a piecewise-linear mapping:
#   score  0–30  → disruption 0%    (low risk, no real disruption)
#   score 30–50  → disruption 0–10% (elevated risk, minor slowdown)
#   score 50–70  → disruption 10–30%(high risk, partial closure)
#   score 70–90  → disruption 30–60%(critical, major interdiction)
#   score 90–100 → disruption 60–90%(near-total blockade)
SCORE_TO_DISRUPTION_BREAKPOINTS = [
    # (score_threshold, disruption_fraction)
    (0,   0.00),
    (30,  0.00),
    (50,  0.10),
    (70,  0.30),
    (90,  0.60),
    (100, 0.90),
]


# ─────────────────────────────────────────────
# 3. SUPPLY DISRUPTION → BRENT CRUDE PRICE
# ─────────────────────────────────────────────

# Baseline Brent crude price (USD/bbl) before any disruption.
# This is the "current" price the model starts from.
BASELINE_BRENT_USD = 85.0

# Elasticity: how much Brent price rises for each 1% of *global*
# supply removed.  Based on the Abqaiq 2019 event:
#   5% supply removal → ~15% price spike on day 1
#   → elasticity ≈ 3.0  (15% / 5%)
# Cross-checked with IEA/IMF short-run supply elasticity studies
# that give 2.5–4.0 range.
BRENT_SUPPLY_ELASTICITY = 3.0

# Price trajectory decay profile.
# After the initial spike, prices decay back toward baseline over
# ~30 days (if disruption is temporary) or sustain (if prolonged).
# These are multipliers of the peak delta at each day.
# Calibrated from Abqaiq 2019 actual data:
#   Day 0: 1.00 (baseline)
#   Day 1: peak (multiplier 1.0 of delta)
#   Day 3: 0.85  (moderation begins)
#   Day 7: 0.55  (stabilizing)
#   Day 14: 0.25 (mostly recovered)
#   Day 30: 0.05 (near baseline)
#
# For sustained disruptions (score >= 80), the decay is slower.
PRICE_TRAJECTORY_DAYS = [0, 1, 3, 7, 14, 30]

# Decay multipliers for a "transient" disruption (quick Saudi-style fix)
DECAY_TRANSIENT = [0.0, 1.0, 0.85, 0.55, 0.25, 0.05]

# Decay multipliers for a "sustained" disruption (ongoing conflict)
DECAY_SUSTAINED = [0.0, 1.0, 0.95, 0.90, 0.80, 0.65]

# Threshold: if risk score >= this, use sustained decay curve
SUSTAINED_THRESHOLD = 80


# ─────────────────────────────────────────────
# 4. BRENT PRICE → INR/USD EXCHANGE RATE
# ─────────────────────────────────────────────

# Baseline INR/USD rate before disruption.
BASELINE_INR_USD = 85.50  # mid-2026 rate

# Elasticity: for every 10% rise in Brent, INR depreciates by X%.
# Based on RBI research papers and historical analysis:
#   2019 Abqaiq: Brent +15%, INR moved ~0.5-1.0%
#   Historical regression: ~1.5-2.0% INR depreciation per 10% Brent rise
# We use 1.8% as the central estimate.
INR_DEPRECIATION_PER_10PCT_BRENT = 1.8  # percent

# The RBI smooths FX moves over several days. This lag factor
# means INR depreciation is spread over ~7 days rather than instant.
# Source: RBI Annual Report 2024-25, FX intervention discussion.
INR_LAG_DAYS = 7

# INR trajectory days (fewer points than Brent — currency moves slower)
INR_TRAJECTORY_DAYS = [0, 7, 14, 30]


# ─────────────────────────────────────────────
# 5. BRENT + INR → DOMESTIC FUEL PRICE
# ─────────────────────────────────────────────

# Baseline domestic petrol price (INR/litre), Delhi benchmark.
# Source: PPAC daily price bulletin, July 2026.
BASELINE_FUEL_PRICE_INR = 96.72

# Pass-through fraction: what share of the international price
# increase actually shows up at the pump.
# India's OMCs absorb ~40-50% of the shock (via under-recoveries
# and excise duty adjustments). So pass-through is ~50-60%.
# Source: PPAC pricing mechanism analysis, thecore.in asymmetry study.
FUEL_PASSTHROUGH_FRACTION = 0.55

# Fuel price adjustments happen with a lag (not daily anymore).
# Typical revision delay is 7-14 days.
FUEL_LAG_DAYS = 14

# Fuel trajectory days
FUEL_TRAJECTORY_DAYS = [0, 7, 14, 30]

# Crude-to-retail factor: $1/bbl change in crude ≈ how many INR/litre
# change at the pump (before pass-through dampening).
# A barrel is ~159 litres, but refining yields ~50% petrol/diesel,
# plus taxes (excise ~₹20 + VAT ~₹15-20), dealer margin etc.
# Empirical: $10/bbl rise ≈ ₹5-6/litre at pump before taxes.
# Source: PPAC retail pricing formula decomposition.
CRUDE_TO_RETAIL_INR_PER_DOLLAR = 0.55  # INR/litre per $1/bbl change


# ─────────────────────────────────────────────
# 6. STATE-LEVEL STRESS INDEX
# ─────────────────────────────────────────────

# Each state has a "vulnerability weight" based on:
#   - Refining capacity (higher = more exposed to import cost)
#   - Petrochemical industry concentration
#   - Transport/logistics dependency on diesel
#   - Industrial energy intensity
#   - Agricultural pump-set dependency (for UP, Rajasthan)
#
# Weights are 0.0–1.0 (1.0 = most vulnerable).
# Source: PPAC refinery list, chemicals.gov.in, state GSDP composition.
STATE_VULNERABILITY = {
    "Gujarat":         0.95,  # Jamnagar, Vadinar, Koyali — dominant refining hub
    "Maharashtra":     0.78,  # BPCL/HPCL Mumbai, large industrial base
    "Tamil Nadu":      0.68,  # CPCL Chennai, auto/manufacturing sector
    "Uttar Pradesh":   0.58,  # Mathura refinery, massive transport network
    "Rajasthan":       0.52,  # Barmer refinery, transport-heavy, agriculture
    "Odisha":          0.48,  # Paradip refinery, growing petrochemical hub
}

# The stress index is computed as:
#   stress = vulnerability_weight × (normalized_brent_delta + normalized_fuel_delta) / 2
# capped at 1.0.


# ─────────────────────────────────────────────
# 7. GDP DRAG
# ─────────────────────────────────────────────

# GDP drag per $10/bbl sustained Brent increase (percentage points).
# Source: RBI Monetary Policy Report, ET/Upstox analysis:
#   Range 0.2–0.5% per $10/bbl. We use 0.35% as central estimate.
GDP_DRAG_PER_10_DOLLAR_BRENT = 0.35  # percentage points

# Maximum GDP drag cap (even in extreme scenarios, other factors
# limit the direct oil-price channel).
GDP_DRAG_MAX = 2.5  # percentage points


# ─────────────────────────────────────────────
# 8. CONFIDENCE MAPPING
# ─────────────────────────────────────────────

# Map risk score ranges to output confidence levels.
# Lower scores → more uncertainty about whether disruption happens.
CONFIDENCE_THRESHOLDS = [
    (70, "high"),    # score >= 70 → high confidence in disruption
    (50, "medium"),  # score >= 50 → medium
    (0,  "low"),     # score < 50  → low
]
