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
    
    # 1. Validate total weights
    total_weight = args.cost_weight + args.time_weight + args.diversification_weight + args.relationship_weight
    if not (0.99 <= total_weight <= 1.01):
        print(f"Warning: Scoring weights sum to {total_weight:.2f} instead of 1.0. Normalizing weights...")
        args.cost_weight /= total_weight
        args.time_weight /= total_weight
        args.diversification_weight /= total_weight
        args.relationship_weight /= total_weight

    print("=== Rakshak AI: Layer 3 (Act) - Sourcing & Route Ranking ===")
    print(f"Loading input file: {args.input}")
    
    # 2. Load schemas and input data
    try:
        schema_l2 = load_json_file(args.schema_l2)
        schema_l3 = load_json_file(args.schema_l3)
        input_data = load_json_file(args.input)
    except Exception as e:
        print(f"Error loading required schema or input files: {e}")
        return 1
        
    # 3. Validate Layer 2 input data against schema
    if not validate_json(input_data, schema_l2):
        print("Error: Input data does not match Layer 2 schema.")
        return 1
    print("[OK] Input data validated successfully against Layer 2 schema.")

    # 4. Load Refineries DB and find the selected refinery
    try:
        refineries = load_json_file(args.refineries_db)
    except Exception as e:
        print(f"Error loading refineries database: {e}")
        return 1
        
    refinery_profile = None
    for ref in refineries:
        if ref["name"].lower() == args.refinery.lower() or ref["name"].lower().startswith(args.refinery.lower()):
            refinery_profile = ref
            break
            
    if not refinery_profile:
        print(f"Error: Target refinery '{args.refinery}' not found in refineries database.")
        print("Available refineries:")
        for ref in refineries:
            print(f"  - {ref['name']} ({ref['type']})")
        return 1
    
    print(f"Target Refinery Profile: {refinery_profile['name']}")
    print(f"  - Location: {refinery_profile['location']}")
    print(f"  - Configuration: {refinery_profile['description']}")
    print(f"  - Compatible Grades: {refinery_profile['compatible_grades']}")

    # 5. Load Alternative Routes DB
    try:
        routes_db = load_json_file(args.routes_db)
    except Exception as e:
        print(f"Error loading routes database: {e}")
        return 1
    print(f"Loaded {len(routes_db)} alternative sourcing options from database.")

    # 6. Extract scenario indicators from Layer 2 input
    scenario_id = input_data["scenario_id"]
    trigger_corridor = input_data["trigger_corridor"].lower()
    trigger_score = input_data["trigger_score"]
    
    # Extract the Brent price projection
    # We will use the day 0 projection value as our current spot brent baseline for calculations
    brent_price_usd = None
    for proj in input_data["projections"]["brent_price_usd"]:
        if proj["day"] == 0:
            brent_price_usd = proj["value"]
            break
    if brent_price_usd is None:
        brent_price_usd = input_data["projections"]["brent_price_usd"][0]["value"]
        
    print(f"Scenario Context: {scenario_id} | Disrupted Corridor: {trigger_corridor} (Stress: {trigger_score})")
    print(f"Current Post-Disruption Brent Crude Price: ${brent_price_usd:.2f}/bbl")
    
    # Fixed pre-disruption baseline Brent crude price (under normal conditions)
    baseline_brent_usd = 75.00
    
    # 7. Filter and evaluate each route
    processed_options = []
    
    # Technical values for freight calculations:
    # Operating cost per nautical mile (fuel + charter amortization) normalized per barrel:
    tanker_freight_factors = {
        "VLCC": 0.000119,     # Large capacity (~2M bbls), highly cost-efficient
        "Suezmax": 0.000178,  # Medium capacity (~1M bbls)
        "Aframax": 0.000210   # Lower capacity (~750k bbls), higher cost per bbl
    }
    
    for route_info in routes_db:
        crude_grade = route_info["crude_grade"].lower()
        
        # A. Grade compatibility hard filter
        is_compatible = crude_grade in refinery_profile["compatible_grades"]
        
        # Skip if incompatible
        if not is_compatible:
            print(f"  [Excluded] {route_info['source_supplier']} ({route_info['crude_type_details']}) - Incompatible grade for {refinery_profile['name']}")
            continue
            
        # B. Calculate delivered spot price
        # Freight cost calculation
        tanker_class = route_info["tanker_class"]
        distance = route_info["distance_nautical_miles"]
        freight_factor = tanker_freight_factors.get(tanker_class, 0.0002)
        freight_cost = distance * freight_factor
        
        # Risk premium calculation if the route transits the disrupted corridor
        risk_premium = 0.0
        is_disrupted_transit = route_info["route_transits_hormuz"] and trigger_corridor == "hormuz"
        if is_disrupted_transit:
            # Risk premium scaled linearly with trigger score (up to $15/bbl for 100% stress)
            risk_premium = (trigger_score / 100.0) * 15.0
            
        # Final post-disruption delivered spot price
        spot_price = brent_price_usd + route_info["base_differential_vs_brent"] + freight_cost + risk_premium
        
        # C. Calculate baseline cost under normal conditions (no disruption, Brent = $75, risk_premium = 0)
        normal_delivered_cost = baseline_brent_usd + route_info["base_differential_vs_brent"] + freight_cost
        
        # Cost delta percentage vs normal baseline
        cost_delta_pct = ((spot_price - normal_delivered_cost) / normal_delivered_cost) * 100.0
        
        # D. Calculate lead times and transit times
        transit_time_hours = distance / 14.0  # Assumes typical tanker speed of 14 knots
        
        # Congestion delay mapping
        congestion_delays = {
            "low": 24.0,
            "medium": 72.0,
            "high": 168.0
        }
        congestion_delay = congestion_delays.get(route_info["port_congestion_factor"], 24.0)
        
        # If route transits a disrupted corridor, add significant congestion/waiting delays
        if is_disrupted_transit:
            # Scaled delay up to additional 7 days (168 hours) for 100% stress
            congestion_delay += (trigger_score / 100.0) * 168.0
            
        # Tanker lead time based on availability
        tanker_lead_time_hours = route_info["tanker_lead_time_hours"]
        
        # Total time to execute
        total_time_hours = tanker_lead_time_hours + transit_time_hours + congestion_delay
        
        # E. Score each dimension out of 100 (where higher is better)
        # Cost Score: 100 at 0% delta, decreases linearly by 3 points per 1% price increase
        cost_score = max(0.0, 100.0 - cost_delta_pct * 3.0)
        
        # Time Score: Shorter lead time is better. 100 at 0 hours, decreases by 2 points per day
        time_score = max(0.0, 100.0 - (total_time_hours / 24.0) * 2.0)
        
        # Diversification Score: Maps qualitative value to scores
        div_val = route_info["diversification_value"].lower()
        if "high" in div_val:
            diversification_score = 100.0
        elif "medium" in div_val:
            diversification_score = 60.0
        else:
            diversification_score = 20.0
            
        # Relationship Score: Inverse of relationship cost friction
        rel_cost = route_info["relationship_cost"].lower()
        if rel_cost == "low":
            relationship_score = 100.0
        elif rel_cost == "medium":
            relationship_score = 60.0
        else:
            relationship_score = 20.0
            
        # F. Compute final weighted score
        final_score = (
            (cost_score * args.cost_weight) +
            (time_score * args.time_weight) +
            (diversification_score * args.diversification_weight) +
            (relationship_score * args.relationship_weight)
        )
        
        # G. Construct detailed rationale
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
        
    # Sort options by final score descending
    processed_options.sort(key=lambda x: x["final_score"], reverse=True)
    
    # 8. Format output structure matching Layer 3 schema
    recommendations_list = []
    for rank_idx, opt in enumerate(processed_options, 1):
        # Remove score helper field from schema-compliant output
        rec = opt.copy()
        rec["rank"] = rank_idx
        del rec["final_score"]
        recommendations_list.append(rec)
        
    output_data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "triggered_by_scenario": scenario_id,
        "recommendations": recommendations_list
    }
    
    # 9. Validate final Layer 3 output against schema
    if not validate_json(output_data, schema_l3):
        print("Error: Generated recommendations do not comply with the Layer 3 schema.")
        return 1
    print("[OK] Generated recommendations validated successfully against Layer 3 schema.")
    
    # 10. Write to output file
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"[OK] Ranked recommendations saved successfully to: {args.output}")
    except Exception as e:
        print(f"Error saving output JSON file: {e}")
        return 1
        
    # 11. Display Ranked Output Table
    print("\n" + "="*80)
    print(f" RANKED ALTERNATIVE SOURCING OPTIONS FOR REFINERY: {refinery_profile['name'].upper()}")
    print("="*80)
    
    table_rows = []
    for rec in recommendations_list:
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
    for rec in recommendations_list[:3]:
        print(f"\n[Rank {rec['rank']}] {rec['source_supplier']}")
        print(f"  Route: {rec['route']}")
        print(f"  Rationale: {rec['rationale']}")
        
    return 0

if __name__ == "__main__":
    exit(main())
