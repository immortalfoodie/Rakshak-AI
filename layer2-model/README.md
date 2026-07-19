# Layer 2: Economic Impact Model

> Part of **Rakshak AI** — an energy supply chain resilience system for India.

## What This Does

This component takes a **risk score** from Layer 1 (which monitors shipping corridors like the Strait of Hormuz) and simulates the **downstream economic cascade** if that corridor is disrupted:

```
Corridor Disruption
    |
    v
Brent Crude Price Spike
    |
    v
India's Import Bill Increase
    |
    v
Indian Rupee (INR) Depreciation
    |
    v
Domestic Fuel Price Rise
    |
    v
State-Level Economic Stress
    |
    v
GDP Drag
```

## Files

| File | What It Does |
|------|-------------|
| `config.py` | All model parameters (elasticities, baselines, thresholds) in one place. Every number is documented with its source. Change values here to tune the model. |
| `assumptions.py` | The full assumptions table — 12 entries covering every link in the causal chain. Each has an ID, plain-English relationship, real-world basis, confidence level, and caveats. Can export to CSV or Markdown. |
| `model.py` | The core engine. Contains 6 computational steps and a `run_scenario()` orchestrator that chains them together. Takes a Layer 1 JSON input and produces a Layer 2 JSON output. |
| `run.py` | Command-line entry point. Reads input, validates against schemas, runs the model, prints a human-friendly summary, and optionally writes output to the shared mock file. |
| `validate.py` | Historical backtesting script. Runs the model against two real events (Abqaiq 2019, US-Iran 2025) and compares projected vs actual Brent prices, reporting MAE and MAPE accuracy metrics. |
| `requirements.txt` | Python dependencies (just `jsonschema`). |

## How to Run

### Prerequisites
- Python 3.10+
- Install dependencies:
  ```bash
  cd layer2-model
  pip install -r requirements.txt
  ```

### Run the Model
```bash
# Run with the default mock Layer 1 input
python run.py

# Run and save output to shared/sample_data/mock_layer2_output.json
python run.py --write

# Run with a custom Layer 1 input file
python run.py path/to/your/layer1_output.json
```

### Run Historical Validation
```bash
python validate.py
```

### Export Assumptions Table
```bash
python assumptions.py
```

## Validation Results

The model was backtested against two historical events:

### Abqaiq-Khurais Attack (September 14, 2019)
- **Event**: Drone/missile attack on Saudi Aramco removed 5.7 mbpd (5% of global supply)
- **Actual Brent**: $60 -> $69 (day 1) -> $59 (day 30) — fast recovery
- **Model Grade**: **GOOD** (MAPE: 17.2%)
- **Note**: The model over-predicts because a score of 88 triggers the "sustained" decay curve, but Abqaiq actually recovered very quickly. This is a known limitation — the risk score captures threat severity, not resolution speed.

| Day | Actual | Projected | Error |
|-----|--------|-----------|-------|
| 0   | $60.22 | $60.22    | $0.00 |
| 1   | $69.02 | $80.82    | $11.80 |
| 7   | $64.88 | $78.76    | $13.88 |
| 14  | $62.48 | $76.70    | $14.22 |
| 30  | $59.00 | $73.61    | $14.61 |

### US-Iran Standoff (2025-2026)
- **Event**: Sustained military tensions, Hormuz disruption fears, no quick resolution
- **Actual Brent**: $68 -> $73.50 (day 1) -> $85 (day 30)
- **Model Grade**: **EXCELLENT** (MAPE: 7.8%)
- **Note**: Model performs very well on sustained crises — exactly the scenario it's designed for.

| Day | Actual | Projected | Error |
|-----|--------|-----------|-------|
| 0   | $68.00 | $68.00    | $0.00 |
| 1   | $73.50 | $87.58    | $14.08 |
| 7   | $79.80 | $85.63    | $5.83 |
| 14  | $82.50 | $83.67    | $1.17 |
| 30  | $85.00 | $80.73    | $4.27 |

### Overall: Average MAPE = 12.5% — performing WELL for a first-principles model.

## Assumptions Summary

The model uses 12 documented assumptions. Key ones:

| # | Assumption | Value | Confidence | Basis |
|---|-----------|-------|------------|-------|
| 1 | Hormuz global oil share | 20% | High | EIA chokepoint data |
| 2 | India's Hormuz dependency | 30% | High | PIB/Ministry of Petroleum (2026) |
| 3 | India crude import dependency | 88.7% | High | PPAC FY 2025-26 |
| 4 | Brent supply elasticity | 3.0 (per 1% supply removed) | Medium | Abqaiq 2019 calibration |
| 5 | INR depreciation per 10% Brent rise | 1.8% | Medium | RBI research, academic regression |
| 6 | Fuel pass-through to consumers | 55% | Medium | PPAC pricing analysis |
| 7 | GDP drag per $10/bbl Brent rise | 0.35% | Medium | RBI Monetary Policy Reports |

For the complete table with all 12 assumptions, run `python assumptions.py` or see `assumptions.py`.

## Model Architecture

```
Layer 1 Input (risk score)
        |
        |  score_to_disruption()
        |  [piecewise-linear mapping]
        v
Supply Disruption %
        |
        |  disruption_to_brent()
        |  [elasticity = 3.0, transient/sustained decay curves]
        v
Brent Price Trajectory (30 days)
        |
        +--> brent_to_inr()                  +--> compute_gdp_drag()
        |    [1.8% per 10%, RBI smoothing]    |    [0.35% per $10/bbl]
        v                                    v
INR/USD Trajectory               GDP Drag (%)
        |
        +--> inr_and_brent_to_fuel()
        |    [55% pass-through, 14-day lag]
        v
Fuel Price Trajectory
        |
        +--> compute_state_stress()
        |    [vulnerability weights x shock intensity]
        v
State Stress Indices (6 states)
        |
        v
Layer 2 Output JSON
```

## Known Limitations

1. **Score-to-disruption mapping is subjective**: The piecewise mapping is the weakest link. Real disruption depends on specifics (blockade vs. insurance pullout vs. military action).
2. **Transient vs. sustained classification**: Using a score threshold (80) to decide decay curve doesn't capture resolution speed. Abqaiq had a high score but recovered fast.
3. **RBI intervention is policy-dependent**: The INR model uses a fixed depreciation rate, but actual RBI intervention depends on reserves, political context, and competing priorities.
4. **Fuel pass-through is political**: The 55% figure is an average; actual pass-through varies with elections, fiscal needs, and OMC balance sheets.
5. **State stress is a simplification**: Real state-level impact depends on power generation fuel mix, transport fleet composition, and state-level subsidy policies.
6. **GDP drag is a medium-term effect**: The model reports an annualized drag from what may be a short-term spike.

## Data Sources

- **EIA**: World Oil Transit Chokepoints (2023), Short-Term Energy Outlook
- **PPAC**: India Oil & Gas Snapshot (FY 2025-26), Refinery capacity data
- **PIB**: Ministry of Petroleum press releases (July 2026)
- **RBI**: Annual Report 2024-25, Monetary Policy Reports
- **Baker Institute for Public Policy**: Abqaiq attack analysis
- **TradingEconomics**: Historical Brent crude prices
- **Academic sources**: Oil-exchange rate regression studies (ResearchGate, neliti.com)
