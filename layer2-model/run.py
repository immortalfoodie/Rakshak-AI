"""
run.py — Command-line entry point for the Layer 2 model.

What this file does:
  1. Reads a Layer 1 output JSON file (default: the mock file in shared/)
  2. Validates it against the Layer 1 schema
  3. Runs the economic impact model
  4. Validates the output against the Layer 2 schema
  5. Prints the output JSON to the console
  6. Optionally writes it to shared/sample_data/mock_layer2_output.json

Usage:
    python run.py                           # uses default mock input
    python run.py path/to/layer1.json       # uses custom input
    python run.py --write                   # also overwrites mock_layer2_output.json
"""

import json
import os
import sys

# Add this directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model import run_scenario

# Paths (relative to the repo root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DEFAULT_INPUT = os.path.join(REPO_ROOT, "shared", "sample_data", "mock_layer1_output.json")
L1_SCHEMA = os.path.join(REPO_ROOT, "shared", "schemas", "layer1_output.schema.json")
L2_SCHEMA = os.path.join(REPO_ROOT, "shared", "schemas", "layer2_output.schema.json")
MOCK_L2_OUTPUT = os.path.join(REPO_ROOT, "shared", "sample_data", "mock_layer2_output.json")


def validate_json(data: dict, schema_path: str, label: str):
    """Validate a dict against a JSON Schema file. Prints result."""
    try:
        import jsonschema
        with open(schema_path, "r") as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        print(f"  [OK] {label} schema validation passed")
    except ImportError:
        print(f"  [WARN] jsonschema not installed -- skipping {label} validation")
        print(f"    Install with: pip install jsonschema")
    except Exception as e:
        print(f"  [FAIL] {label} schema validation FAILED: {e}")
        return False
    return True


def main():
    # Parse arguments
    input_path = DEFAULT_INPUT
    write_output = False

    for arg in sys.argv[1:]:
        if arg == "--write":
            write_output = True
        elif arg == "--help":
            print(__doc__)
            sys.exit(0)
        else:
            input_path = arg

    # 1. Read input
    print(f"\n{'='*60}")
    print(f"  RAKSHAK AI — Layer 2 Economic Impact Model")
    print(f"{'='*60}")
    print(f"\n[1] Reading Layer 1 input from: {input_path}")

    with open(input_path, "r") as f:
        layer1_input = json.load(f)

    print(f"    Corridor: {layer1_input['corridor']}")
    print(f"    Score:    {layer1_input['score']}")
    print(f"    Alert:    {layer1_input['alert_level']}")

    # 2. Validate input
    print(f"\n[2] Validating input...")
    validate_json(layer1_input, L1_SCHEMA, "Layer 1 input")

    # 3. Run model
    print(f"\n[3] Running economic impact model...")
    output = run_scenario(layer1_input)

    # 4. Print summary
    print(f"\n[4] Results Summary:")
    proj = output["projections"]
    brent = proj["brent_price_usd"]
    print(f"    Scenario:  {output['scenario_id']}")
    print(f"    Confidence: {output['confidence']}")
    print(f"\n    Brent Crude (USD/bbl):")
    for p in brent:
        marker = " <- peak" if p["value"] == max(x["value"] for x in brent) else ""
        print(f"      Day {p['day']:3d}: ${p['value']:7.2f}{marker}")

    print("\n    INR/USD Rate:")
    for p in proj["inr_usd_rate"]:
        print(f"      Day {p['day']:3d}: Rs.{p['value']:.2f}")

    print(f"\n    Domestic Fuel Price (INR/litre):")
    for p in proj["domestic_fuel_price_inr_per_liter"]:
        print(f"      Day {p['day']:3d}: Rs.{p['value']:.2f}")

    print(f"\n    State Stress Index:")
    for s in proj["state_impact"]:
        bar = "#" * int(s["stress_index"] * 20)
        print(f"      {s['state']:20s}: {s['stress_index']:.2f} {bar}")

    print(f"\n    GDP Drag: {proj['gdp_drag_pct']:.2f}%")

    # 5. Validate output
    print(f"\n[5] Validating output...")
    validate_json(output, L2_SCHEMA, "Layer 2 output")

    # 6. Print full JSON
    print(f"\n[6] Full output JSON:")
    output_json = json.dumps(output, indent=2)
    print(output_json)

    # 7. Optionally write to file
    if write_output:
        print(f"\n[7] Writing output to: {MOCK_L2_OUTPUT}")
        with open(MOCK_L2_OUTPUT, "w") as f:
            f.write(output_json + "\n")
        print(f"    [OK] Done")
    else:
        print(f"\n    (Use --write flag to save output to mock_layer2_output.json)")

    print(f"\n{'='*60}\n")
    return output


if __name__ == "__main__":
    main()
