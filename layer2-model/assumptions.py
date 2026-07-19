"""
assumptions.py — The full assumptions table for the Layer 2 model.

Each assumption has:
  - id:          short string used in the output JSON's "assumptions_used" list
  - step:        which link in the causal chain this belongs to
  - relationship: plain-English description of the assumed relationship
  - basis:       what real-world data or event this is based on
  - confidence:  High / Medium / Low
  - notes:       caveats or limitations

This file can also export the table as CSV or Markdown.
"""

import csv
import io


ASSUMPTIONS_TABLE = [
    {
        "id": "score_to_disruption_mapping",
        "step": "Risk Score → Supply Disruption",
        "relationship": (
            "A risk score of 72 (high) maps to ~30% flow disruption. "
            "Score 90+ maps to 60-90% disruption (near-total blockade)."
        ),
        "basis": (
            "Calibrated against Abqaiq 2019 (5.7 mbpd removed = ~5% global supply, "
            "equivalent to ~28% of Saudi output). The piecewise mapping is designed "
            "so that a 'high' alert (score 70) corresponds to a partial but significant "
            "disruption, consistent with historical naval standoff scenarios."
        ),
        "confidence": "Medium",
        "notes": (
            "This mapping is subjective — the score-to-disruption curve is the weakest "
            "link in the model. Real disruption severity depends on specifics (blockade "
            "vs. insurance pullout vs. military action) that a single score cannot capture."
        ),
    },
    {
        "id": "hormuz_global_share",
        "step": "Corridor → Global Supply",
        "relationship": (
            "Strait of Hormuz handles ~20% of global oil supply (~20 mbpd "
            "out of ~100 mbpd total)."
        ),
        "basis": (
            "EIA 'World Oil Transit Chokepoints' (2023 update). "
            "Also confirmed by IEA World Energy Outlook 2024."
        ),
        "confidence": "High",
        "notes": "Well-established figure, stable over time.",
    },
    {
        "id": "hormuz_india_share",
        "step": "Corridor → India Import Exposure",
        "relationship": (
            "~30% of India's crude oil imports transit the Strait of Hormuz. "
            "(Down from ~40-45% historically due to diversification.)"
        ),
        "basis": (
            "PIB / Ministry of Petroleum press release (July 2026): "
            "'India now sources approximately 70% of its crude oil imports "
            "from outside the Strait of Hormuz.' Historical PPAC data showed "
            "40-45% Hormuz dependency pre-2023."
        ),
        "confidence": "High",
        "notes": (
            "This figure changes as India diversifies suppliers. "
            "The model should be re-calibrated annually."
        ),
    },
    {
        "id": "india_import_dependency",
        "step": "Corridor → India Import Exposure",
        "relationship": "India imports 88.7% of its crude oil consumption.",
        "basis": (
            "PPAC 'Snapshot of India's Oil & Gas Data' for FY 2025-26. "
            "Consistent with agavart.com analysis citing the same PPAC source."
        ),
        "confidence": "High",
        "notes": "Among the highest import dependencies globally.",
    },
    {
        "id": "brent_supply_elasticity",
        "step": "Supply Disruption → Brent Price",
        "relationship": (
            "Each 1% of global supply removed causes ~3% Brent price increase "
            "(short-run elasticity = 3.0)."
        ),
        "basis": (
            "Abqaiq 2019: 5% global supply removed → ~15% Brent spike (day 1 close), "
            "giving elasticity of 3.0. Cross-checked with IEA/IMF short-run oil supply "
            "elasticity estimates of 2.5–4.0. The 2025-26 US-Iran conflict showed a "
            "28% Brent rise over several weeks of sustained disruption fears."
        ),
        "confidence": "Medium",
        "notes": (
            "Short-run elasticity is highly event-dependent. Abqaiq was a sudden "
            "supply shock with quick recovery. A sustained blockade would follow "
            "a different price path. We use separate decay curves for transient "
            "vs. sustained scenarios."
        ),
    },
    {
        "id": "price_decay_transient",
        "step": "Brent Price Trajectory (Transient)",
        "relationship": (
            "After a sudden supply shock, Brent price spike decays to ~5% of "
            "peak delta within 30 days (fast recovery)."
        ),
        "basis": (
            "Abqaiq 2019 actual prices: Day 1 peak +15%, Day 3 +13%, "
            "Day 7 +8%, Day 14 +3.7%, Day 30 roughly back to baseline. "
            "Saudi Aramco restored production within 2-3 weeks."
        ),
        "confidence": "High",
        "notes": "Only applies when disruption is expected to be temporary.",
    },
    {
        "id": "price_decay_sustained",
        "step": "Brent Price Trajectory (Sustained)",
        "relationship": (
            "In a sustained conflict, Brent remains elevated — retaining ~65% "
            "of peak delta even at day 30."
        ),
        "basis": (
            "2025-26 US-Iran conflict: Brent rose ~28% and remained elevated "
            "for months. Monthly volatility increased from 4.7% to 25.6%. "
            "Unlike Abqaiq, there was no quick resolution."
        ),
        "confidence": "Medium",
        "notes": (
            "The sustained curve is less well-calibrated because ongoing "
            "conflicts don't have a clean 'recovery point'. The 65% retention "
            "at day 30 is a conservative estimate."
        ),
    },
    {
        "id": "inr_oil_depreciation",
        "step": "Brent Price → INR/USD Depreciation",
        "relationship": (
            "For every 10% rise in Brent crude, the INR depreciates by ~1.8% "
            "against USD, spread over ~7 days due to RBI intervention."
        ),
        "basis": (
            "RBI Annual Reports and monetary policy discussions note active "
            "FX intervention to smooth volatility. Academic regression studies "
            "(neliti.com, ResearchGate) find 1.5-2.0% INR depreciation per "
            "10% oil price rise. Abqaiq 2019: Brent +15%, INR moved ~0.5-1.0% "
            "(RBI intervened aggressively). We use 1.8% as central estimate."
        ),
        "confidence": "Medium",
        "notes": (
            "RBI intervention makes this highly policy-dependent. In a crisis "
            "where RBI reserves are stressed, depreciation could be much larger. "
            "The model does not account for capital flight or FII outflows."
        ),
    },
    {
        "id": "fuel_passthrough",
        "step": "Brent + INR → Domestic Fuel Price",
        "relationship": (
            "Only ~55% of international crude price increases are passed through "
            "to domestic petrol/diesel prices, with a ~14-day lag."
        ),
        "basis": (
            "India's OMCs (IOC, BPCL, HPCL) operate under a 'managed pricing' "
            "regime. PPAC data and thecore.in analysis show asymmetric pass-through: "
            "~50-60% of increases reach consumers, but decreases are passed through "
            "even more slowly. The March 2024 ₹2/litre cut after months of stable "
            "crude is a clear example. Excise duty acts as a buffer."
        ),
        "confidence": "Medium",
        "notes": (
            "Pass-through is a political variable — elections, inflation targets, "
            "and fiscal needs all affect it. The 55% figure is an average; actual "
            "pass-through in a crisis could be lower (government absorbs more) "
            "or higher (if OMC losses become unsustainable)."
        ),
    },
    {
        "id": "crude_to_retail_factor",
        "step": "Brent + INR → Domestic Fuel Price",
        "relationship": (
            "$1/bbl crude price change → ~₹0.55/litre change at the pump "
            "(before pass-through dampening)."
        ),
        "basis": (
            "PPAC retail pricing formula decomposition. A barrel is ~159 litres, "
            "refining yield for petrol/diesel is ~50%, plus taxes (excise ₹20 + "
            "VAT ₹15-20) and dealer margin. Empirically, $10/bbl rise → ₹5-6/litre "
            "at the pump before government intervention."
        ),
        "confidence": "Medium",
        "notes": "Sensitive to the tax structure, which changes frequently.",
    },
    {
        "id": "state_vulnerability_weights",
        "step": "Oil Shock → State-Level Stress",
        "relationship": (
            "Gujarat (0.95) is most vulnerable due to Jamnagar/Vadinar/Koyali refineries. "
            "Maharashtra (0.78), Tamil Nadu (0.68), UP (0.58), Rajasthan (0.52), "
            "Odisha (0.48) follow based on refining capacity and industrial mix."
        ),
        "basis": (
            "PPAC refinery capacity data: Gujarat hosts ~40% of national refining "
            "capacity (Jamnagar alone is 68.2 MMTPA). chemicals.gov.in shows "
            "Gujarat+Maharashtra account for >50% of chemical/petrochemical GVA. "
            "State GSDP composition data from RBI Handbook of Statistics."
        ),
        "confidence": "Medium",
        "notes": (
            "The weights are a simplification — actual state stress depends on "
            "power generation fuel mix, transport fleet composition, and state-level "
            "subsidy policies. A more granular model would use sector-specific "
            "input-output tables."
        ),
    },
    {
        "id": "gdp_drag_elasticity",
        "step": "Oil Shock → GDP Impact",
        "relationship": (
            "A sustained $10/bbl increase in Brent crude reduces India's GDP "
            "growth by ~0.35 percentage points."
        ),
        "basis": (
            "RBI Monetary Policy Report estimates. Economic Times, Upstox, and "
            "multibagg.ai analyses all cite 0.2-0.5% GDP drag per $10/bbl. "
            "We use 0.35% as the central estimate. In extreme scenarios "
            "($120-130/bbl), impact could reach 0.5%+ per $10."
        ),
        "confidence": "Medium",
        "notes": (
            "GDP drag is a medium-to-long-term effect (quarters, not days). "
            "The model reports a *projected* annual drag assuming the price "
            "increase is sustained. Actual GDP impact depends on government "
            "response, alternative sourcing, and demand elasticity."
        ),
    },
]


def get_assumptions_ids():
    """Return a list of all assumption IDs."""
    return [a["id"] for a in ASSUMPTIONS_TABLE]


def to_markdown():
    """Export the assumptions table as a formatted Markdown string."""
    lines = [
        "# Layer 2 Model — Assumptions Table",
        "",
        "| # | ID | Step | Relationship | Basis | Confidence | Notes |",
        "|---|-----|------|-------------|-------|------------|-------|",
    ]
    for i, a in enumerate(ASSUMPTIONS_TABLE, 1):
        lines.append(
            f"| {i} | `{a['id']}` | {a['step']} | {a['relationship']} "
            f"| {a['basis']} | **{a['confidence']}** | {a['notes']} |"
        )
    return "\n".join(lines)


def to_csv():
    """Export the assumptions table as a CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "step", "relationship", "basis", "confidence", "notes"],
    )
    writer.writeheader()
    for a in ASSUMPTIONS_TABLE:
        writer.writerow(a)
    return output.getvalue()


if __name__ == "__main__":
    print(to_markdown())
