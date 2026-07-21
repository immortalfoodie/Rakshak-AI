import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the root directory to sys.path so we can import from layer1, layer2, layer3
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import importlib.util

def import_module_from_path(module_name, file_path):
    parent_dir = str(file_path.parent)
    sys.path.insert(0, parent_dir)
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path[0] == parent_dir:
            sys.path.pop(0)

layer1 = import_module_from_path("layer1", ROOT_DIR / "layer1-watch" / "run_pipeline.py")

def run_layer1(corridor: str):
    schema = layer1.load_schema()
    return layer1.run_corridor(corridor, schema)

layer2 = import_module_from_path("layer2", ROOT_DIR / "layer2-model" / "model.py")
run_layer2 = layer2.run_scenario

layer3 = import_module_from_path("layer3", ROOT_DIR / "layer3-act" / "rank_sourcing.py")
run_layer3 = layer3.run_ranking

app = FastAPI(title="Rakshak AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SHARED_DIR = ROOT_DIR / "shared"
SAMPLE_DATA_DIR = SHARED_DIR / "sample_data"

@app.get("/api/historical-replay")
def get_historical_replay(event_id: str = "abqaiq_2019"):
    """Serve the historical replay JSON data."""
    file_path = SAMPLE_DATA_DIR / "historical_events" / f"{event_id}.json"
    if not file_path.exists():
        return {"error": f"Event {event_id} not found."}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/live-status")
def get_live_status(corridor: str = "hormuz", simulate_crisis: bool = False, custom_score: float = None):
    """
    Run the real pipeline end-to-end and return the result.
    This replaces the old mock-based integration/pipeline.py.
    """
    start_time = time.perf_counter()
    latencies = {}
    timestamps = {}

    # Layer 1
    t0 = time.perf_counter()
    layer1_out = run_layer1(corridor=corridor)
    
    if custom_score is not None:
        layer1_out["score"] = custom_score
        layer1_out["alert_level"] = "high" if custom_score >= 80 else ("medium" if custom_score >= 40 else "low")
        layer1_out["sub_scores"] = {
            "custom_override": True
        }
    elif simulate_crisis:
        # Override live data with a fake massive disruption
        # Use static, deterministic scores per corridor so it remains constant per-location
        # but varies across locations to demonstrate dynamic calculation.
        mock_scores = {
            "hormuz": 95.5,
            "red_sea": 88.2,
            "malacca": 81.0,
            "suez": 78.5
        }
        layer1_out["score"] = mock_scores.get(corridor.lower(), 90.0)
        layer1_out["alert_level"] = "high"
        layer1_out["sub_scores"] = {
            "news_sentiment": 98.0,
            "sanctions_delta": 85.0,
            "prediction_market": 96.0,
            "ais_dark_fleet": 80.0,
            "futures_spread": 90.0
        }

    t1 = time.perf_counter()
    latencies["layer1_ingest_ms"] = round((t1 - t0) * 1000, 2)
    timestamps["layer1_received"] = datetime.now(timezone.utc).isoformat()

    # Layer 2
    t2 = time.perf_counter()
    layer2_out = run_layer2(layer1_input=layer1_out)
    t3 = time.perf_counter()
    latencies["layer2_process_ms"] = round((t3 - t2) * 1000, 2)
    timestamps["layer2_complete"] = datetime.now(timezone.utc).isoformat()

    # Layer 3
    t4 = time.perf_counter()
    refineries_db_path = str(ROOT_DIR / "layer3-act" / "refineries.json")
    routes_db_path = str(ROOT_DIR / "layer3-act" / "routes.json")
    layer3_out = run_layer3(
        input_data=layer2_out,
        refinery="Jamnagar (RIL)",
        refineries_db_path=refineries_db_path,
        routes_db_path=routes_db_path
    )
    t5 = time.perf_counter()
    latencies["layer3_process_ms"] = round((t5 - t4) * 1000, 2)
    timestamps["layer3_complete"] = datetime.now(timezone.utc).isoformat()

    total_elapsed = t5 - start_time
    timestamps["pipeline_total_ms"] = round(total_elapsed * 1000, 2)

    return {
        "layer1_output": layer1_out,
        "layer2_output": layer2_out,
        "layer3_output": layer3_out,
        "latencies": latencies,
        "timestamps": timestamps,
        "total_elapsed_ms": round(total_elapsed * 1000, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
