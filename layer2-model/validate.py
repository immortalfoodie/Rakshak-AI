"""
validate.py — Historical backtesting for the Layer 2 model.

What this file does:
  1. Loads two historical events (Abqaiq 2019, US-Iran 2025)
  2. For each event, creates a synthetic Layer 1 input with the
     risk score that the event would have generated
  3. Runs the model with the historical baseline prices
  4. Compares the projected Brent price trajectory against what
     actually happened
  5. Reports accuracy metrics: MAE, MAPE, and a day-by-day comparison

Usage:
    python validate.py
"""

import json
import os
import sys

# Add this directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model import run_scenario, _interpolate_trajectory

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
EVENTS_DIR = os.path.join(REPO_ROOT, "shared", "sample_data", "historical_events")


def load_event(filename: str) -> dict:
    """Load a historical event JSON file."""
    path = os.path.join(EVENTS_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def compare_trajectories(
    projected: list[dict],
    actual: list[dict],
    label: str,
) -> dict:
    """
    Compare projected vs actual Brent price trajectories.

    Returns a dict with:
      - day_by_day: list of comparisons at each actual data point
      - mae: Mean Absolute Error (USD/bbl)
      - mape: Mean Absolute Percentage Error (%)
    """
    comparisons = []
    errors = []
    pct_errors = []

    for actual_point in actual:
        day = actual_point["day"]
        actual_val = actual_point["value"]
        projected_val = _interpolate_trajectory(projected, day)

        error = abs(projected_val - actual_val)
        pct_error = (error / actual_val) * 100 if actual_val != 0 else 0

        errors.append(error)
        pct_errors.append(pct_error)
        comparisons.append({
            "day": day,
            "actual": round(actual_val, 2),
            "projected": round(projected_val, 2),
            "error": round(error, 2),
            "pct_error": round(pct_error, 1),
        })

    mae = sum(errors) / len(errors) if errors else 0
    mape = sum(pct_errors) / len(pct_errors) if pct_errors else 0

    return {
        "day_by_day": comparisons,
        "mae": round(mae, 2),
        "mape": round(mape, 1),
    }


def validate_event(event_data: dict, event_name: str):
    """Run the model against a historical event and report results."""
    print(f"\n{'-'*60}")
    print(f"  Historical Validation: {event_name}")
    print(f"{'-'*60}")

    # Extract event data
    layer1_input = event_data["layer1_input"]
    actual_brent = event_data["actual_brent_trajectory"]
    baseline_brent = event_data["baseline_brent_usd"]
    baseline_inr = event_data.get("baseline_inr_usd", 85.50)
    description = event_data.get("description", "")

    print(f"\n  Event:     {description}")
    print(f"  Corridor:  {layer1_input['corridor']}")
    print(f"  Score:     {layer1_input['score']}")
    print(f"  Baseline:  ${baseline_brent}/bbl")

    # Run model with historical baselines
    output = run_scenario(
        layer1_input,
        baseline_brent=baseline_brent,
        baseline_inr=baseline_inr,
    )

    projected_brent = output["projections"]["brent_price_usd"]

    # Compare
    result = compare_trajectories(projected_brent, actual_brent, event_name)

    # Print day-by-day comparison
    print(f"\n  Day-by-Day Comparison (Brent Crude USD/bbl):")
    print(f"  {'Day':>5s}  {'Actual':>10s}  {'Projected':>10s}  {'Error':>8s}  {'Error%':>8s}")
    print(f"  {'-'*5}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*8}")
    for c in result["day_by_day"]:
        direction = "^" if c["projected"] > c["actual"] else "v" if c["projected"] < c["actual"] else "="
        print(
            f"  {c['day']:5d}  ${c['actual']:9.2f}  ${c['projected']:9.2f}  "
            f"${c['error']:7.2f}  {c['pct_error']:6.1f}% {direction}"
        )

    print(f"\n  Summary Metrics:")
    print(f"    Mean Absolute Error (MAE):  ${result['mae']:.2f}/bbl")
    print(f"    Mean Abs % Error (MAPE):    {result['mape']:.1f}%")

    # Interpret
    if result["mape"] < 10:
        grade = "EXCELLENT"
    elif result["mape"] < 20:
        grade = "GOOD"
    elif result["mape"] < 30:
        grade = "FAIR"
    else:
        grade = "POOR"
    print(f"    Model Grade:                {grade}")

    return result


def main():
    print(f"\n{'='*60}")
    print(f"  RAKSHAK AI -- Layer 2 Model Historical Validation")
    print(f"{'='*60}")

    results = {}

    # Validate Abqaiq 2019
    try:
        abqaiq = load_event("abqaiq_2019.json")
        results["abqaiq_2019"] = validate_event(abqaiq, "Abqaiq-Khurais Attack (Sept 2019)")
    except Exception as e:
        print(f"\n  [WARN] Could not validate Abqaiq 2019: {e}")

    # Validate US-Iran 2025
    try:
        us_iran = load_event("us_iran_2025.json")
        results["us_iran_2025"] = validate_event(us_iran, "US-Iran Standoff (2025-2026)")
    except Exception as e:
        print(f"\n  [WARN] Could not validate US-Iran 2025: {e}")

    # Overall summary
    print(f"\n{'='*60}")
    print(f"  Overall Validation Summary")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"  {name:25s}  MAE: ${r['mae']:5.2f}  MAPE: {r['mape']:5.1f}%")

    if results:
        avg_mape = sum(r["mape"] for r in results.values()) / len(results)
        print(f"\n  Average MAPE across events: {avg_mape:.1f}%")
        if avg_mape < 15:
            print(f"  -> Model is performing WELL for a first-principles model.")
        elif avg_mape < 25:
            print(f"  -> Model is performing REASONABLY -- suitable for scenario analysis.")
        else:
            print(f"  -> Model needs calibration -- consider adjusting elasticities in config.py.")

    print(f"\n{'='*60}\n")
    return results


if __name__ == "__main__":
    main()
