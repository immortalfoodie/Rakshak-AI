"""
Rakshak AI — Integration Pipeline Orchestrator
================================================
Reads Layer 1 output, passes it through Layer 2 and Layer 3 stubs,
records timestamps at each handoff, and calculates total elapsed time.

The layer_*_process functions are **stubs** that return mock data.
Swap them with real HTTP calls / function imports once teammates ship.
"""

import json
import time
import pathlib
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SHARED = pathlib.Path(__file__).resolve().parent.parent / "shared"
SAMPLE = SHARED / "sample_data"
SCHEMAS = SHARED / "schemas"

# ---------------------------------------------------------------------------
# Layer stub functions — REPLACE these with real calls later
# ---------------------------------------------------------------------------

def layer2_process(layer1_output: dict) -> dict:
    """
    Stub for Layer 2 (scenario modelling).
    In production, replace this body with an HTTP call or direct import:
        from layer2 import run_scenario
        return run_scenario(layer1_output)
    """
    time.sleep(0.15)  # simulate processing latency
    with open(SAMPLE / "mock_layer2_output.json", "r") as f:
        return json.load(f)


def layer3_process(layer2_output: dict) -> dict:
    """
    Stub for Layer 3 (procurement recommendations).
    In production, replace this body with an HTTP call or direct import:
        from layer3 import generate_recommendations
        return generate_recommendations(layer2_output)
    """
    time.sleep(0.10)  # simulate processing latency
    with open(SAMPLE / "mock_layer3_output.json", "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class PipelineResult:
    """Container for a single pipeline execution's outputs + timing."""

    def __init__(self):
        self.layer1_output: dict = {}
        self.layer2_output: dict = {}
        self.layer3_output: dict = {}
        self.timestamps: dict[str, str] = {}
        self.latencies: dict[str, float] = {}
        self.total_elapsed: float = 0.0

    def to_dict(self) -> dict:
        return {
            "layer1_output": self.layer1_output,
            "layer2_output": self.layer2_output,
            "layer3_output": self.layer3_output,
            "timestamps": self.timestamps,
            "latencies": self.latencies,
            "total_elapsed_ms": round(self.total_elapsed * 1000, 2),
        }


def run_pipeline(layer1_output: dict | None = None) -> PipelineResult:
    """
    Execute the full 3-layer pipeline.

    Parameters
    ----------
    layer1_output : dict, optional
        If None, reads from shared/sample_data/mock_layer1_output.json.

    Returns
    -------
    PipelineResult
        Outputs from each layer plus timing metadata.
    """
    result = PipelineResult()
    pipeline_start = time.perf_counter()

    # --- Layer 1 ingestion ---
    t0 = time.perf_counter()
    if layer1_output is None:
        with open(SAMPLE / "mock_layer1_output.json", "r") as f:
            layer1_output = json.load(f)
    result.layer1_output = layer1_output
    t1 = time.perf_counter()
    result.timestamps["layer1_received"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer1_ingest_ms"] = round((t1 - t0) * 1000, 2)

    # --- Layer 2 processing ---
    t2 = time.perf_counter()
    result.layer2_output = layer2_process(layer1_output)
    t3 = time.perf_counter()
    result.timestamps["layer2_complete"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer2_process_ms"] = round((t3 - t2) * 1000, 2)

    # --- Layer 3 processing ---
    t4 = time.perf_counter()
    result.layer3_output = layer3_process(result.layer2_output)
    t5 = time.perf_counter()
    result.timestamps["layer3_complete"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer3_process_ms"] = round((t5 - t4) * 1000, 2)

    result.total_elapsed = t5 - pipeline_start
    result.timestamps["pipeline_total_ms"] = round(result.total_elapsed * 1000, 2)

    return result


def run_pipeline_with_custom_data(
    layer1: dict, layer2: dict, layer3: dict
) -> PipelineResult:
    """
    Run pipeline using fully pre-supplied data for all three layers.
    Used by historical replay mode.
    """
    result = PipelineResult()
    pipeline_start = time.perf_counter()

    # Layer 1
    result.layer1_output = layer1
    result.timestamps["layer1_received"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer1_ingest_ms"] = 0.0

    # Layer 2
    t2 = time.perf_counter()
    time.sleep(0.05)  # small simulated latency for realism
    result.layer2_output = layer2
    t3 = time.perf_counter()
    result.timestamps["layer2_complete"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer2_process_ms"] = round((t3 - t2) * 1000, 2)

    # Layer 3
    t4 = time.perf_counter()
    time.sleep(0.03)
    result.layer3_output = layer3
    t5 = time.perf_counter()
    result.timestamps["layer3_complete"] = datetime.now(timezone.utc).isoformat()
    result.latencies["layer3_process_ms"] = round((t5 - t4) * 1000, 2)

    result.total_elapsed = t5 - pipeline_start
    result.timestamps["pipeline_total_ms"] = round(result.total_elapsed * 1000, 2)

    return result


# ---------------------------------------------------------------------------
# CLI entry point (for quick testing)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    res = run_pipeline()
    print(json.dumps(res.to_dict(), indent=2))
