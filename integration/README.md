# Rakshak AI — Integration Layer

The **integration layer** is the glue that connects the three independently-built components of Rakshak AI:

| Layer | Component | What it does |
|-------|-----------|--------------|
| 1 | `layer1-watch` | Monitors shipping corridors (Hormuz, Red Sea) and outputs a fused **risk score** |
| 2 | `layer2-model` | Takes the risk score and projects **economic impact** (Brent price, INR rate, fuel prices) |
| 3 | `layer3-act` | Takes projections and generates **ranked procurement recommendations** |

This integration layer orchestrates data flow between all three, provides a **web dashboard** for visualization, and includes a **historical replay mode** for demos.

---

## Quick Start

```bash
# 1. Navigate to the integration folder
cd integration

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

The dashboard will open at **http://localhost:8501**.

---

## What You'll See

### Live Pipeline Mode (default)
- **Risk Score Ring** — Overall corridor risk score from Layer 1
- **Signal Sub-Scores** — News sentiment, sanctions delta, AIS dark fleet, prediction markets, futures spread
- **Geospatial Map** — Dark-themed map (Leaflet via Folium) showing:
  - The monitored corridor region (Strait of Hormuz / Red Sea)
  - Mock AIS vessel positions (including "dark fleet" vessels)
  - Recommended alternative shipping routes from Layer 3, plotted as dashed polylines
- **Scenario Projections** — Line charts for Brent price, INR/USD rate, and domestic fuel price over a 14-day horizon
- **State Stress Index** — Bar chart of Indian states most impacted
- **Procurement Recommendations** — Ranked cards with supplier, route, cost delta, lead time, and rationale
- **Latency Log** — Timestamps at each pipeline handoff and total elapsed time

### Historical Replay Mode
Toggle to **🔁 Historical Replay** in the sidebar to:
1. Select a historical event (e.g., *Abqaiq–Khurais Attack 2019* or *US–Iran Escalation 2025*)
2. Set replay speed (0.5x–5x)
3. Watch the dashboard animate through each step of the crisis at accelerated speed

---

## Project Structure

```
integration/
├── app.py              # Streamlit dashboard (main entry point)
├── pipeline.py         # Orchestration script with Layer 2/3 stubs
├── config.py           # Paths, geo coordinates, route waypoints, mock vessels
├── map_builder.py      # Folium map construction
├── charts.py           # Plotly chart builders
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## How to Swap in Real Layer Code

The pipeline stubs are in **`pipeline.py`**. Each layer has a clearly marked function:

### Layer 2 (`layer2_process`)
```python
# Current stub (line ~30):
def layer2_process(layer1_output: dict) -> dict:
    with open(SAMPLE / "mock_layer2_output.json") as f:
        return json.load(f)

# Replace with real call:
def layer2_process(layer1_output: dict) -> dict:
    import requests
    resp = requests.post("http://layer2-service:8000/run", json=layer1_output)
    return resp.json()
    # OR: from layer2.model import run_scenario; return run_scenario(layer1_output)
```

### Layer 3 (`layer3_process`)
```python
# Current stub (line ~42):
def layer3_process(layer2_output: dict) -> dict:
    with open(SAMPLE / "mock_layer3_output.json") as f:
        return json.load(f)

# Replace with real call:
def layer3_process(layer2_output: dict) -> dict:
    import requests
    resp = requests.post("http://layer3-service:8000/recommend", json=layer2_output)
    return resp.json()
    # OR: from layer3.engine import generate_recommendations; return generate_recommendations(layer2_output)
```

### Layer 1 (input)
Layer 1 output is read from `shared/sample_data/mock_layer1_output.json` by default.
To use a real Layer 1 feed, pass data directly:
```python
from pipeline import run_pipeline
result = run_pipeline(layer1_output=real_layer1_data)
```

---

## Adding Historical Events

Add new JSON files to `shared/sample_data/historical_events/`. Each file should follow this structure:

```json
{
  "event_id": "unique_id",
  "event_name": "Human-readable name",
  "description": "What happened",
  "steps": [
    {
      "step": 1,
      "delay_seconds": 3,
      "layer1": { ... },
      "layer2": { ... },
      "layer3": { ... }
    }
  ]
}
```

Each step must contain valid Layer 1, 2, and 3 output objects matching the schemas in `shared/schemas/`.

---

## Testing the Pipeline (CLI)

```bash
python pipeline.py
```

This runs the full pipeline with mock data and prints JSON output with timing metadata.

---

## Data Contracts

All inter-layer data must conform to the JSON schemas in `shared/schemas/`:
- `layer1_output.schema.json` — Risk score with sub-scores and evidence
- `layer2_output.schema.json` — Scenario projections (prices, exchange rates, state impact)
- `layer3_output.schema.json` — Ranked procurement recommendations

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Runtime |
| Streamlit | Dashboard framework |
| Plotly | Interactive charts |
| Folium | Geospatial mapping (Leaflet-based) |
| streamlit-folium | Folium integration for Streamlit |
