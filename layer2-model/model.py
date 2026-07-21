"""
model.py — Core causal-chain engine for the Layer 2 economic impact model.

This file contains the functions that simulate the downstream economic
cascade when a shipping corridor is disrupted:

  1. score_to_disruption()        — risk score → supply disruption %
  2. disruption_to_brent()        — supply disruption → Brent price trajectory
  3. brent_to_inr()               — Brent spike → INR/USD depreciation
  4. inr_and_brent_to_fuel()      — combined effect → domestic fuel price
  5. compute_state_stress()       — fuel/oil shock → state-level stress index
  6. compute_gdp_drag()           — oil price change → national GDP drag
  7. run_scenario()               — orchestrator: takes Layer 1 input, returns
                                     a Layer 2 output dict matching the schema

All parameters come from config.py.  All assumption IDs come from assumptions.py.
"""

import uuid
import random
from datetime import datetime, timezone

from layer2_config import (
    CORRIDOR_GLOBAL_SHARE,
    CORRIDOR_INDIA_SHARE,
    INDIA_IMPORT_DEPENDENCY,
    SCORE_TO_DISRUPTION_BREAKPOINTS,
    BASELINE_BRENT_USD,
    BRENT_SUPPLY_ELASTICITY,
    PRICE_TRAJECTORY_DAYS,
    DECAY_TRANSIENT,
    DECAY_SUSTAINED,
    SUSTAINED_THRESHOLD,
    BASELINE_INR_USD,
    INR_DEPRECIATION_PER_10PCT_BRENT,
    INR_LAG_DAYS,
    INR_TRAJECTORY_DAYS,
    BASELINE_FUEL_PRICE_INR,
    FUEL_PASSTHROUGH_FRACTION,
    FUEL_LAG_DAYS,
    FUEL_TRAJECTORY_DAYS,
    CRUDE_TO_RETAIL_INR_PER_DOLLAR,
    STATE_VULNERABILITY,
    GDP_DRAG_PER_10_DOLLAR_BRENT,
    GDP_DRAG_MAX,
    CONFIDENCE_THRESHOLDS,
)
from assumptions import get_assumptions_ids


# ─────────────────────────────────────────────
# 1. RISK SCORE → SUPPLY DISRUPTION
# ─────────────────────────────────────────────

def score_to_disruption(score: float) -> float:
    """
    Convert a 0–100 risk score to a supply disruption fraction (0.0–1.0).

    Uses piecewise-linear interpolation between the breakpoints defined
    in config.SCORE_TO_DISRUPTION_BREAKPOINTS.

    Example:
        score=72 → ~0.306 (about 30.6% of corridor flow disrupted)
    """
    breakpoints = SCORE_TO_DISRUPTION_BREAKPOINTS
    if score <= breakpoints[0][0]:
        return breakpoints[0][1]
    if score >= breakpoints[-1][0]:
        return breakpoints[-1][1]

    for i in range(len(breakpoints) - 1):
        s0, d0 = breakpoints[i]
        s1, d1 = breakpoints[i + 1]
        if s0 <= score <= s1:
            # Linear interpolation
            t = (score - s0) / (s1 - s0) if s1 != s0 else 0.0
            return d0 + t * (d1 - d0)

    return breakpoints[-1][1]


# ─────────────────────────────────────────────
# 2. SUPPLY DISRUPTION → BRENT PRICE TRAJECTORY
# ─────────────────────────────────────────────

def disruption_to_brent(
    disruption_fraction: float,
    corridor: str,
    score: float,
    baseline_brent: float = None,
) -> list[dict]:
    """
    Project a Brent crude price trajectory over 30 days.

    Args:
        disruption_fraction: 0.0–1.0 fraction of corridor flow cut
        corridor: corridor identifier (e.g. "hormuz")
        score: original risk score (used to pick transient vs sustained decay)
        baseline_brent: starting Brent price (defaults to config value)

    Returns:
        List of {"day": int, "value": float} dicts.

    Logic:
        1. Compute global supply reduction = disruption × corridor's global share
        2. Price spike % = supply_reduction × elasticity
        3. Apply decay curve (transient or sustained based on score)
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD

    global_share = CORRIDOR_GLOBAL_SHARE.get(corridor, 0.10)
    supply_reduction_pct = disruption_fraction * global_share * 100  # in %

    # Peak price increase (%)
    peak_pct_increase = supply_reduction_pct * BRENT_SUPPLY_ELASTICITY

    # Choose decay curve
    decay = DECAY_SUSTAINED if score >= SUSTAINED_THRESHOLD else DECAY_TRANSIENT

    trajectory = []
    for day, multiplier in zip(PRICE_TRAJECTORY_DAYS, decay):
        delta = baseline_brent * (peak_pct_increase / 100.0) * multiplier
        price = round(baseline_brent + delta, 2)
        trajectory.append({"day": day, "value": price})

    return trajectory


# ─────────────────────────────────────────────
# 3. BRENT PRICE → INR/USD DEPRECIATION
# ─────────────────────────────────────────────

def brent_to_inr(
    brent_trajectory: list[dict],
    baseline_brent: float = None,
    baseline_inr: float = None,
) -> list[dict]:
    """
    Project INR/USD exchange rate based on Brent price movement.

    The INR depreciation is proportional to the Brent price increase,
    but smoothed over INR_LAG_DAYS due to RBI intervention.

    Returns:
        List of {"day": int, "value": float} dicts.
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD
    if baseline_inr is None:
        baseline_inr = BASELINE_INR_USD

    # Find the peak Brent increase (%)
    peak_brent_pct = 0.0
    for point in brent_trajectory:
        pct_change = ((point["value"] - baseline_brent) / baseline_brent) * 100
        if pct_change > peak_brent_pct:
            peak_brent_pct = pct_change

    # INR depreciation (%)
    inr_depreciation_pct = (peak_brent_pct / 10.0) * INR_DEPRECIATION_PER_10PCT_BRENT

    # Build INR trajectory with lag smoothing
    trajectory = []
    for day in INR_TRAJECTORY_DAYS:
        if day == 0:
            trajectory.append({"day": 0, "value": round(baseline_inr, 2)})
        else:
            # Ramp up depreciation over the lag period, then hold
            ramp = min(day / INR_LAG_DAYS, 1.0)

            # After the initial ramp, check if Brent is recovering
            # (which would ease INR pressure)
            brent_at_day = _interpolate_trajectory(brent_trajectory, day)
            current_brent_pct = ((brent_at_day - baseline_brent) / baseline_brent) * 100
            sustain_factor = current_brent_pct / peak_brent_pct if peak_brent_pct > 0 else 0

            effective_depreciation = inr_depreciation_pct * ramp * max(sustain_factor, 0.3)
            inr_value = baseline_inr * (1 + effective_depreciation / 100.0)
            trajectory.append({"day": day, "value": round(inr_value, 2)})

    return trajectory


# ─────────────────────────────────────────────
# 4. BRENT + INR → DOMESTIC FUEL PRICE
# ─────────────────────────────────────────────

def inr_and_brent_to_fuel(
    brent_trajectory: list[dict],
    inr_trajectory: list[dict],
    baseline_brent: float = None,
    baseline_inr: float = None,
    baseline_fuel: float = None,
) -> list[dict]:
    """
    Project domestic petrol price (INR/litre) based on Brent and INR moves.

    The domestic price change comes from two sources:
      1. Crude price increase (in USD) → converted to INR using current rate
      2. INR depreciation → makes the same USD price more expensive in INR

    Both are dampened by the FUEL_PASSTHROUGH_FRACTION and delayed by FUEL_LAG_DAYS.

    Returns:
        List of {"day": int, "value": float} dicts.
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD
    if baseline_inr is None:
        baseline_inr = BASELINE_INR_USD
    if baseline_fuel is None:
        baseline_fuel = BASELINE_FUEL_PRICE_INR

    trajectory = []
    for day in FUEL_TRAJECTORY_DAYS:
        if day == 0:
            trajectory.append({"day": 0, "value": round(baseline_fuel, 2)})
        else:
            # Get Brent and INR at this day
            brent_at_day = _interpolate_trajectory(brent_trajectory, day)
            inr_at_day = _interpolate_trajectory(inr_trajectory, day)

            # Crude price delta (USD/bbl)
            crude_delta_usd = brent_at_day - baseline_brent

            # Convert crude delta to INR/litre impact
            crude_impact_inr = crude_delta_usd * CRUDE_TO_RETAIL_INR_PER_DOLLAR

            # INR depreciation impact: same crude price costs more in INR
            inr_depreciation_factor = inr_at_day / baseline_inr
            inr_impact = baseline_fuel * (inr_depreciation_factor - 1.0)

            # Total raw impact
            total_raw_impact = crude_impact_inr + inr_impact

            # Apply pass-through dampening and lag
            lag_factor = min(day / FUEL_LAG_DAYS, 1.0)
            dampened_impact = total_raw_impact * FUEL_PASSTHROUGH_FRACTION * lag_factor

            fuel_price = baseline_fuel + dampened_impact
            trajectory.append({"day": day, "value": round(fuel_price, 2)})

    return trajectory


# ─────────────────────────────────────────────
# 5. STATE-LEVEL STRESS INDEX
# ─────────────────────────────────────────────

def compute_state_stress(
    brent_trajectory: list[dict],
    fuel_trajectory: list[dict],
    baseline_brent: float = None,
    baseline_fuel: float = None,
) -> list[dict]:
    """
    Compute stress index (0.0–1.0) for each state.

    Stress = vulnerability_weight × shock_intensity
    where shock_intensity is a normalized measure of how much Brent and
    fuel prices have moved (using peak values from trajectory).

    Returns:
        List of {"state": str, "stress_index": float} dicts, sorted by stress.
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD
    if baseline_fuel is None:
        baseline_fuel = BASELINE_FUEL_PRICE_INR

    # Peak Brent change (normalized to 0–1 scale, where 30% increase = 1.0)
    peak_brent = max(p["value"] for p in brent_trajectory)
    brent_norm = min(((peak_brent - baseline_brent) / baseline_brent) / 0.30, 1.0)

    # Peak fuel change (normalized to 0–1 scale, where 15% increase = 1.0)
    peak_fuel = max(p["value"] for p in fuel_trajectory)
    fuel_norm = min(((peak_fuel - baseline_fuel) / baseline_fuel) / 0.15, 1.0)

    # Combined shock intensity
    shock_intensity = (brent_norm + fuel_norm) / 2.0

    results = []
    for state, weight in STATE_VULNERABILITY.items():
        stress = round(min(weight * shock_intensity, 1.0), 2)
        results.append({"state": state, "stress_index": stress})

    # Sort by stress descending
    results.sort(key=lambda x: x["stress_index"], reverse=True)
    return results


# ─────────────────────────────────────────────
# 6. GDP DRAG
# ─────────────────────────────────────────────

def compute_gdp_drag(
    brent_trajectory: list[dict],
    baseline_brent: float = None,
) -> float:
    """
    Estimate the GDP drag (in percentage points) from the oil price shock.

    Uses the average Brent increase over the trajectory period (weighted
    toward later days, since GDP impact is a sustained-price effect).

    Returns:
        GDP drag as a positive percentage (e.g. 0.4 means 0.4% drag).
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD

    # Use the "sustained" Brent level — average of day 7 and day 14 prices
    # (GDP impact comes from weeks/months of elevated prices, not day-1 spike)
    sustained_prices = [
        p["value"] for p in brent_trajectory if p["day"] >= 7
    ]
    if not sustained_prices:
        sustained_prices = [p["value"] for p in brent_trajectory]

    avg_sustained = sum(sustained_prices) / len(sustained_prices)
    delta_usd = avg_sustained - baseline_brent

    # GDP drag per $10 increase
    gdp_drag = (delta_usd / 10.0) * GDP_DRAG_PER_10_DOLLAR_BRENT

    # Cap and floor
    gdp_drag = max(0.0, min(gdp_drag, GDP_DRAG_MAX))
    return round(gdp_drag, 2)


# ─────────────────────────────────────────────
# 7. SPR DEPLETION
# ─────────────────────────────────────────────

def compute_spr_depletion(score: float) -> dict:
    """
    Calculates Strategic Petroleum Reserve (SPR) depletion based on risk score.
    Higher risk = higher drawdown multiplier.
    """
    # 0 score = 1.0x multiplier, 100 score = 2.5x multiplier
    multiplier = 1.0 + (score / 100.0) * 1.5
    days_remaining = 9.5 / multiplier
    return {
        "current_reserve_volume_mmt": 5.33,
        "base_days_of_cover": 9.5,
        "drawdown_multiplier": round(multiplier, 2),
        "days_remaining": round(days_remaining, 1)
    }


# ─────────────────────────────────────────────
# 8. CONFIDENCE LEVEL
# ─────────────────────────────────────────────

def score_to_confidence(score: float) -> str:
    """Map a risk score to a confidence level string."""
    for threshold, level in CONFIDENCE_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


# ─────────────────────────────────────────────
# 9. MONTE CARLO SIMULATION
# ─────────────────────────────────────────────

def simulate_monte_carlo_brent(
    disruption_fraction: float,
    corridor: str,
    score: float,
    baseline_brent: float = None,
    iterations: int = 200,
) -> list[dict]:
    """
    Runs a Monte Carlo simulation (default 200 iterations) to find the 10th and 90th
    percentile confidence intervals for the Brent price trajectory by perturbing
    the elasticity and baseline parameters randomly.
    """
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD

    # 1. Generate the median/baseline trajectory
    median_traj = disruption_to_brent(disruption_fraction, corridor, score, baseline_brent)

    # 2. Run iterations with perturbed parameters
    # We will perturb the BRENT_SUPPLY_ELASTICITY (global variable used in disruption_to_brent)
    # by +/- 20% using a normal distribution.
    # We'll use a hack to temporarily override the global or just implement the math directly here.
    # To keep it clean, we'll just run the math directly for the bounds:
    
    global_share = CORRIDOR_GLOBAL_SHARE.get(corridor, 0.10)
    supply_reduction_pct = disruption_fraction * global_share * 100
    decay = DECAY_SUSTAINED if score >= SUSTAINED_THRESHOLD else DECAY_TRANSIENT

    daily_prices = {day: [] for day in PRICE_TRAJECTORY_DAYS}

    for _ in range(iterations):
        # Perturb elasticity (std dev of 10% of base)
        perturbed_elasticity = random.gauss(BRENT_SUPPLY_ELASTICITY, BRENT_SUPPLY_ELASTICITY * 0.10)
        # Perturb baseline Brent slightly
        perturbed_baseline = random.gauss(baseline_brent, baseline_brent * 0.05)
        
        peak_pct_increase = supply_reduction_pct * perturbed_elasticity
        
        for day, multiplier in zip(PRICE_TRAJECTORY_DAYS, decay):
            delta = perturbed_baseline * (peak_pct_increase / 100.0) * multiplier
            price = perturbed_baseline + delta
            daily_prices[day].append(price)

    # 3. Calculate p10 and p90 for each day and merge into median trajectory
    for point in median_traj:
        day = point["day"]
        sorted_prices = sorted(daily_prices[day])
        p10 = sorted_prices[int(0.10 * iterations)]
        p90 = sorted_prices[int(0.90 * iterations)]
        
        point["lower"] = round(p10, 2)
        point["upper"] = round(p90, 2)

    return median_traj

# ─────────────────────────────────────────────
# 10. SCENARIO ORCHESTRATOR
# ─────────────────────────────────────────────

def run_scenario(
    layer1_input: dict,
    baseline_brent: float = None,
    baseline_inr: float = None,
    baseline_fuel: float = None,
) -> dict:
    """
    Main entry point: takes a Layer 1 output dict and produces a
    Layer 2 output dict that matches the schema.

    Args:
        layer1_input: dict conforming to layer1_output.schema.json
        baseline_brent: optional override for starting Brent price
        baseline_inr: optional override for starting INR/USD rate
        baseline_fuel: optional override for starting fuel price

    Returns:
        dict conforming to layer2_output.schema.json
    """
    corridor = layer1_input["corridor"]
    score = layer1_input["score"]
    input_ts = layer1_input.get("timestamp", datetime.now(timezone.utc).isoformat())

    # Use defaults from config if not overridden
    if baseline_brent is None:
        baseline_brent = BASELINE_BRENT_USD
    if baseline_inr is None:
        baseline_inr = BASELINE_INR_USD
    if baseline_fuel is None:
        baseline_fuel = BASELINE_FUEL_PRICE_INR

    # Step 1: Score → disruption
    disruption = score_to_disruption(score)

    # Step 2: Disruption → Brent trajectory (with real Monte Carlo bounds)
    brent_traj = simulate_monte_carlo_brent(disruption, corridor, score, baseline_brent)

    # Step 3: Brent → INR trajectory
    inr_traj = brent_to_inr(brent_traj, baseline_brent, baseline_inr)

    # Step 4: Brent + INR → Fuel trajectory
    fuel_traj = inr_and_brent_to_fuel(
        brent_traj, inr_traj, baseline_brent, baseline_inr, baseline_fuel
    )

    # Step 5: State stress
    state_stress = compute_state_stress(
        brent_traj, fuel_traj, baseline_brent, baseline_fuel
    )

    # Step 6: GDP drag
    gdp_drag = compute_gdp_drag(brent_traj, baseline_brent)
    
    # Step 7: SPR Depletion
    spr_depletion = compute_spr_depletion(score)

    # Step 8: Confidence
    confidence = score_to_confidence(score)

    # Build scenario ID
    disruption_label = f"{int(disruption * 100)}pct"
    scenario_id = f"{corridor}_disruption_{disruption_label}"

    # Produce output
    output = {
        "scenario_id": scenario_id,
        "trigger_corridor": corridor,
        "trigger_score": score,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence": confidence,
        "assumptions_used": get_assumptions_ids(),
        "projections": {
            "brent_price_usd": brent_traj,
            "inr_usd_rate": inr_traj,
            "domestic_fuel_price_inr_per_liter": fuel_traj,
            "state_impact": state_stress,
            "gdp_drag_pct": gdp_drag,
            "spr_depletion": spr_depletion,
        },
    }

    return output


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _interpolate_trajectory(trajectory: list[dict], target_day: int) -> float:
    """
    Linearly interpolate a value from a trajectory at a given day.
    If target_day is beyond the last point, return the last value.
    """
    if not trajectory:
        return 0.0

    # Exact match
    for point in trajectory:
        if point["day"] == target_day:
            return point["value"]

    # Interpolate
    for i in range(len(trajectory) - 1):
        d0, v0 = trajectory[i]["day"], trajectory[i]["value"]
        d1, v1 = trajectory[i + 1]["day"], trajectory[i + 1]["value"]
        if d0 <= target_day <= d1:
            t = (target_day - d0) / (d1 - d0)
            return v0 + t * (v1 - v0)

    # Beyond last point — return last value
    return trajectory[-1]["value"]
