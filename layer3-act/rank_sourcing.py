#!/usr/bin/env python3
"""
Rakshak AI - Layer 3 (Act) Sourcing & Route Ranking System
This script processes scenario output from Layer 2 (disruption scenario model),
filters alternative crude oil sourcing options based on refinery compatibility,
ranks them based on cost, lead time, diversification, and relationship friction,
and outputs a structured recommendation plan matching the Layer 3 schema.
"""

import os
import json
import argparse
from datetime import datetime, timezone
from jsonschema import validate, ValidationError
from tabulate import tabulate

def run_ranking(
    input_data: dict,
    refinery: str,
    refineries_db_path: str,
    routes_db_path: str,
    schema_l3_path: str = None,
    cost_weight: float = 0.40,
    time_weight: float = 0.20,
    diversification_weight: float = 0.25,
    relationship_weight: float = 0.15
) -> dict:
    # 1. Validate total weights
    total_weight = cost_weight + time_weight + diversification_weight + relationship_weight
    if not (0.99 <= total_weight <= 1.01):
        cost_weight /= total_weight
        time_weight /= total_weight
        diversification_weight /= total_weight
        relationship_weight /= total_weight

    # 4. Load Refineries DB and find the selected refinery
    refineries = load_json_file(refineries_db_path)
    refinery_profile = None
    for ref in refineries:
        if ref["name"].lower() == refinery.lower() or ref["name"].lower().startswith(refinery.lower()):
            refinery_profile = ref
            break
            
    if not refinery_profile:
        raise ValueError(f"Target refinery '{refinery}' not found in refineries database.")
    
    # 5. Load Alternative Routes DB
    routes_db = load_json_file(routes_db_path)

    # 6. Extract scenario indicators from Layer 2 input
    scenario_id = input_data["scenario_id"]
    trigger_corridor = input_data["trigger_corridor"].lower()
    trigger_score = input_data["trigger_score"]
    
    # Extract the Brent price projection
    brent_price_usd = None
    for proj in input_data["projections"]["brent_price_usd"]:
        if proj["day"] == 0:
            brent_price_usd = proj["value"]
            break
    if brent_price_usd is None:
        brent_price_usd = input_data["projections"]["brent_price_usd"][0]["value"]
        
    # Fixed pre-disruption baseline Brent crude price (under normal conditions)
    baseline_brent_usd = 75.00
    
    # 7. Filter and evaluate each route
    processed_options = []
    
    # Technical values for freight calculations:
    tanker_freight_factors = {
        "VLCC": 0.000119,
        "Suezmax": 0.000178,
        "Aframax": 0.000210
    }
    
    for route_info in routes_db:
        crude_grade = route_info["crude_grade"].lower()
        
        # A. Grade compatibility hard filter
        is_compatible = crude_grade in refinery_profile["compatible_grades"]
        
        # Skip if incompatible
        if not is_compatible:
            continue
            
        # B. Calculate delivered spot price
        tanker_class = route_info["tanker_class"]
        distance = route_info["distance_nautical_miles"]
        freight_factor = tanker_freight_factors.get(tanker_class, 0.0002)
        freight_cost = distance * freight_factor
        
        # Risk premium calculation
        risk_premium = 0.0
        is_disrupted_transit = False
        if trigger_corridor == "hormuz" and route_info.get("route_transits_hormuz", False):
            is_disrupted_transit = True
        elif trigger_corridor == "malacca" and route_info.get("route_transits_malacca", False):
            is_disrupted_transit = True
        elif trigger_corridor == "suez" and route_info.get("route_transits_suez", False):
            is_disrupted_transit = True
            
        if is_disrupted_transit:
            risk_premium = (trigger_score / 100.0) * 15.0
            
        spot_price = brent_price_usd + route_info["base_differential_vs_brent"] + freight_cost + risk_premium
        normal_delivered_cost = baseline_brent_usd + route_info["base_differential_vs_brent"] + freight_cost
        cost_delta_pct = ((spot_price - normal_delivered_cost) / normal_delivered_cost) * 100.0
        
        transit_time_hours = distance / 14.0
        congestion_delays = {"low": 24.0, "medium": 72.0, "high": 168.0}
        congestion_delay = congestion_delays.get(route_info["port_congestion_factor"], 24.0)
        
        if is_disrupted_transit:
            congestion_delay += (trigger_score / 100.0) * 168.0
            
        tanker_lead_time_hours = route_info["tanker_lead_time_hours"]
        total_time_hours = tanker_lead_time_hours + transit_time_hours + congestion_delay
        
        cost_score = max(0.0, 100.0 - cost_delta_pct * 3.0)
        time_score = max(0.0, 100.0 - (total_time_hours / 24.0) * 2.0)
        
        div_val = route_info["diversification_value"].lower()
        if "high" in div_val: diversification_score = 100.0
        elif "medium" in div_val: diversification_score = 60.0
        else: diversification_score = 20.0
            
        rel_cost = route_info["relationship_cost"].lower()
        if rel_cost == "low": relationship_score = 100.0
        elif rel_cost == "medium": relationship_score = 60.0
        else: relationship_score = 20.0
            
        final_score = (
            (cost_score * cost_weight) +
            (time_score * time_weight) +
            (diversification_score * diversification_weight) +
            (relationship_score * relationship_weight)
        )
        
        bypass_desc = "bypasses the disrupted Strait of Hormuz" if not route_info["route_transits_hormuz"] else "transits the disrupted Strait of Hormuz (subject to risk premiums and transit delays)"
        refinery_msg = f"Fully compatible with {refinery_profile['name']}'s {refinery_profile['type']} crude configuration."
        
        if is_disrupted_transit:
            rationale_text = (
                f"{refinery_msg} While it uses established contracts, transiting the Strait of Hormuz "
                f"during this active disruption adds a high risk premium (+${risk_premium:.2f}/bbl) "
                f"and severe transit congestion (+{(trigger_score / 100.0) * 168.0:.1f}h delay), making it expensive and slow."
            )
        elif route_info["relationship_cost"] == "high":
            rationale_text = (
                f"Highly compatible {crude_grade} grade that {bypass_desc}. Shipped via {tanker_class} in {total_time_hours/24.0:.1f} days. "
                f"Offers the highest discount (delivered spot price of ${spot_price:.2f}/bbl, differential of ${route_info['base_differential_vs_brent']:.2f}/bbl), "
                f"but carries high relationship friction due to G7 sanctions compliance and insurance waiver requirements."
            )
        elif route_info["relationship_cost"] == "low" and not route_info["route_transits_hormuz"] and "medium" in div_val:
            rationale_text = (
                f"Excellent bypass option utilizing Middle East export terminals outside the Gulf ({bypass_desc}). "
                f"Extremely fast transit time ({total_time_hours/24.0:.1f} days total) using active long-term agreements with zero sanctions friction, "
                f"yielding low relationship cost and steady tanker availability."
            )
        else:
            rationale_text = (
                f"High-diversification alternative loaded completely outside the Middle East. Shipped via {tanker_class} "
                f"over {distance:,} NM ({transit_time_hours/24.0:.1f} days sea voyage). Restructures the supply chain to "
                f"eliminate Hormuz exposure with zero geopolitical friction, though subject to standard spot premiums."
            )
            
        processed_options.append({
            "source_supplier": route_info["source_supplier"],
            "route": route_info["route"],
            "tanker_class": route_info["tanker_class"],
            "tanker_availability": route_info["tanker_availability_status"],
            "refinery_grade_match": True,
            "spot_price_usd_per_bbl": round(spot_price, 2),
            "cost_delta_vs_baseline_pct": round(cost_delta_pct, 1),
            "time_to_execute_hours": round(total_time_hours, 1),
            "port_congestion_factor": route_info["port_congestion_factor"],
            "diversification_value": route_info["diversification_value"],
            "relationship_cost": route_info["relationship_cost"],
            "rationale": rationale_text,
            "final_score": final_score
        })
        
    processed_options.sort(key=lambda x: x["final_score"], reverse=True)
    
    # Keep only the top 5 recommendations
    processed_options = processed_options[:5]
    
    recommendations_list = []
    for rank_idx, opt in enumerate(processed_options, 1):
        rec = opt.copy()
        rec["rank"] = rank_idx
        del rec["final_score"]
        recommendations_list.append(rec)
        
    output_data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by_scenario": scenario_id,
        "recommendations": recommendations_list
    }
    
    if schema_l3_path:
        schema_l3 = load_json_file(schema_l3_path)
        if not validate_json(output_data, schema_l3):
            raise ValueError("Generated recommendations do not comply with the Layer 3 schema.")
            
    return output_data


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rank alternative crude oil sourcing options and shipping routes for Indian refiners during supply disruptions."
    )
    parser.add_argument(
        "--input", "-i",
        default=os.path.join("shared", "sample_data", "mock_layer2_output.json"),
        help="Path to the Layer 2 scenario projection JSON input file"
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join("shared", "sample_data", "mock_layer3_output.json"),
        help="Path to save the ranked Layer 3 output JSON file"
    )
    parser.add_argument(
        "--refinery", "-r",
        default="Jamnagar (RIL)",
        help="Target refinery name from refineries database (e.g. 'Jamnagar (RIL)', 'Digboi (IOCL)')"
    )
    parser.add_argument(
        "--refineries-db",
        default=os.path.join("layer3-act", "refineries.json"),
        help="Path to the refineries configuration database JSON file"
    )
    parser.add_argument(
        "--routes-db",
        default=os.path.join("layer3-act", "routes.json"),
        help="Path to the alternative shipping routes database JSON file"
    )
    parser.add_argument(
        "--schema-l2",
        default=os.path.join("shared", "schemas", "layer2_output.schema.json"),
        help="Path to the Layer 2 input validation schema JSON file"
    )
    parser.add_argument(
        "--schema-l3",
        default=os.path.join("shared", "schemas", "layer3_output.schema.json"),
        help="Path to the Layer 3 output validation schema JSON file"
    )
    
    # Ranking Weights (must sum to 1.0)
    parser.add_argument("--cost-weight", type=float, default=0.40, help="Weight for Cost Score (0.0 to 1.0)")
    parser.add_argument("--time-weight", type=float, default=0.20, help="Weight for Time Score (0.0 to 1.0)")
    parser.add_argument("--diversification-weight", type=float, default=0.25, help="Weight for Diversification Score (0.0 to 1.0)")
    parser.add_argument("--relationship-weight", type=float, default=0.15, help="Weight for Relationship Score (0.0 to 1.0)")
    
    return parser.parse_args()

def load_json_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Database/File not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_json(data, schema):
    try:
        validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        print(f"Schema validation error details:\n{e.message}")
        print(f"Failed element path: {' -> '.join(map(str, e.absolute_path))}")
        return False

def main():
    args = parse_args()
    
    print("=== Rakshak AI: Layer 3 (Act) - Sourcing & Route Ranking ===")
    print(f"Loading input file: {args.input}")
    
    try:
        schema_l2 = load_json_file(args.schema_l2)
        input_data = load_json_file(args.input)
    except Exception as e:
        print(f"Error loading required schema or input files: {e}")
        return 1
        
    if not validate_json(input_data, schema_l2):
        print("Error: Input data does not match Layer 2 schema.")
        return 1
    print("[OK] Input data validated successfully against Layer 2 schema.")

    try:
        output_data = run_ranking(
            input_data=input_data,
            refinery=args.refinery,
            refineries_db_path=args.refineries_db,
            routes_db_path=args.routes_db,
            schema_l3_path=args.schema_l3,
            cost_weight=args.cost_weight,
            time_weight=args.time_weight,
            diversification_weight=args.diversification_weight,
            relationship_weight=args.relationship_weight
        )
    except Exception as e:
        print(f"Error during ranking: {e}")
        return 1

    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"[OK] Ranked recommendations saved successfully to: {args.output}")
    except Exception as e:
        print(f"Error saving output JSON file: {e}")
        return 1
        
    print("\n" + "="*80)
    print(f" RANKED ALTERNATIVE SOURCING OPTIONS FOR REFINERY: {args.refinery.upper()}")
    print("="*80)
    
    table_rows = []
    for rec in output_data["recommendations"]:
        table_rows.append([
            rec["rank"],
            rec["source_supplier"],
            rec["tanker_class"],
            f"${rec['spot_price_usd_per_bbl']:.2f}",
            f"+{rec['cost_delta_vs_baseline_pct']}%" if rec['cost_delta_vs_baseline_pct'] > 0 else f"{rec['cost_delta_vs_baseline_pct']}%",
            f"{rec['time_to_execute_hours']/24.0:.1f} days",
            rec["relationship_cost"],
            rec["port_congestion_factor"]
        ])
        
    print(tabulate(
        table_rows,
        headers=["Rank", "Supplier Source", "Tanker", "Spot Price", "Cost Delta", "Time to Act", "Relation Cost", "Congestion"],
        tablefmt="grid"
    ))
    
    print("\nDetailed rationales for top selections:")
    for rec in output_data["recommendations"][:3]:
        print(f"\n[Rank {rec['rank']}] {rec['source_supplier']}")
        print(f"  Route: {rec['route']}")
        print(f"  Rationale: {rec['rationale']}")
        
    return 0

if __name__ == "__main__":
    exit(main())
