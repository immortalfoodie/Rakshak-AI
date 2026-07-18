#!/usr/bin/env python3
"""
run_pipeline.py — Live risk scoring pipeline for layer1-watch.

Fetches live signals from GDELT, OFAC, and Polymarket (all free, no API keys),
fuses them into a per-corridor risk score, validates the output against the
layer1_output.schema.json contract, and writes output JSON files.

Signal availability summary
───────────────────────────
  news_sentiment    → GDELT 2.0 DOC API    (free, always attempted)
  sanctions_delta   → OFAC SDN CSV         (free, always attempted)
  prediction_market → Polymarket CLOB API  (free; null if no relevant market)
  ais_dark_fleet    → null                 (no free AIS transponder-gap API)
  futures_spread    → null                 (no free real-time futures feed)

Output
──────
  layer1-watch/output/CORRIDOR_YYYYMMDD_HHMMSS.json   (per corridor)
  shared/sample_data/mock_layer1_output.json           (hormuz output, for demos)

Usage
─────
  python run_pipeline.py                  # all three corridors
  python run_pipeline.py --corridor hormuz
  python run_pipeline.py --validate-only  # just check the schema file loads
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow direct execution from the layer1-watch directory
sys.path.insert(0, str(Path(__file__).parent))

import jsonschema

from config import CORRIDORS, MOCK_OUTPUT_PATH, OUTPUT_DIR, SCHEMA_PATH
from signals import gdelt_signal, ofac_signal, polymarket_signal
from scoring.fuser import build_sub_scores, fuse

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_pipeline")


# ── Schema helpers ────────────────────────────────────────────────────────────

def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def validate_output(output: dict, schema: dict) -> bool:
    try:
        jsonschema.validate(instance=output, schema=schema)
        return True
    except jsonschema.ValidationError as exc:
        logger.error("Schema validation failed: %s", exc.message)
        return False


# ── Per-corridor pipeline ─────────────────────────────────────────────────────

def run_corridor(corridor: str, schema: dict) -> "dict | None":
    """
    Run the full signal → fuse → validate pipeline for one corridor.

    Returns the validated output dict, or None if validation failed.
    """
    logger.info("══ Corridor: %s (%s) ══", corridor, CORRIDORS[corridor]["name"])

    # 1. Fetch signals (each returns score-or-None + evidence list)
    logger.info("[%s] Fetching GDELT news signal …", corridor)
    news_score, news_evidence = gdelt_signal.fetch_live(corridor)

    logger.info("[%s] Fetching OFAC sanctions signal …", corridor)
    sanc_score, sanc_evidence = ofac_signal.fetch_live(corridor)

    logger.info("[%s] Fetching Polymarket prediction-market signal …", corridor)
    pm_score, pm_evidence = polymarket_signal.fetch_live(corridor)

    # 2. Build sub-scores dict (ais + futures always None)
    sub_scores = build_sub_scores(news_score, sanc_score, pm_score)

    # 3. Fuse into overall score
    overall_score, alert_level = fuse(sub_scores)

    # 4. Assemble evidence trail
    all_evidence = news_evidence + sanc_evidence + pm_evidence

    # 5. Build output object
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {
        "corridor":    corridor,
        "timestamp":   now_iso,
        "score":       overall_score,
        "alert_level": alert_level,
        "sub_scores":  sub_scores,
        "evidence":    all_evidence,
    }

    # 6. Validate against schema
    if not validate_output(output, schema):
        logger.error("[%s] Output FAILED schema validation — skipping write", corridor)
        return None

    logger.info(
        "[%s] ✓ score=%.1f  alert=%-8s  news=%-6s  sanctions=%-6s  polymarket=%s",
        corridor,
        overall_score,
        alert_level,
        f"{news_score:.1f}" if news_score is not None else "null",
        f"{sanc_score:.1f}" if sanc_score is not None else "null",
        f"{pm_score:.1f}"   if pm_score   is not None else "null",
    )
    return output


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="layer1-watch — live geopolitical risk pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Output JSON files are written to layer1-watch/output/",
    )
    parser.add_argument(
        "--corridor",
        choices=list(CORRIDORS.keys()),
        default=None,
        help="Run for a single corridor only (default: all three)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Load and print the schema, then exit without fetching data",
    )
    args = parser.parse_args()

    schema = load_schema()
    logger.info("Schema loaded: %s", SCHEMA_PATH.name)

    if args.validate_only:
        print(f"✓ Schema OK — {SCHEMA_PATH}")
        return

    corridors_to_run = [args.corridor] if args.corridor else list(CORRIDORS.keys())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for corridor in corridors_to_run:
        output = run_corridor(corridor, schema)
        if output is None:
            continue
        results.append(output)

        # Write per-corridor timestamped file
        ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = OUTPUT_DIR / f"{corridor}_{ts_slug}.json"
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        logger.info("Written → %s", out_path)

        # Keep the shared mock file up-to-date with the hormuz corridor output
        if corridor == "hormuz":
            MOCK_OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
            logger.info("Updated → %s", MOCK_OUTPUT_PATH)

    if not results:
        logger.error("No valid outputs produced. Check logs above.")
        sys.exit(1)

    # Summary table
    print("\n" + "═" * 65)
    print("  PIPELINE SUMMARY")
    print("═" * 65)
    header = f"  {'Corridor':<18} {'Score':>6}  {'Alert':<10}  {'News':>6}  {'Sanctions':>9}  {'PM':>6}"
    print(header)
    print("  " + "─" * 63)
    for r in results:
        ss = r["sub_scores"]
        news = f"{ss['news_sentiment']:.1f}" if ss["news_sentiment"] is not None else "null"
        sanc = f"{ss['sanctions_delta']:.1f}" if ss["sanctions_delta"] is not None else "null"
        pm   = f"{ss['prediction_market']:.1f}" if ss["prediction_market"] is not None else "null"
        print(
            f"  {r['corridor']:<18} {r['score']:>6.1f}  {r['alert_level']:<10}  "
            f"{news:>6}  {sanc:>9}  {pm:>6}"
        )
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()
