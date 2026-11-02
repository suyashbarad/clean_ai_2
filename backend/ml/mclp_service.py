import math
from typing import List, Dict, Any
from backend.ml.dbscan_service import haversine_distance_meters

def solve_mclp(
    existing_bins: List[Dict[str, Any]],
    demand_points: List[Dict[str, Any]],
    candidate_locations: List[Dict[str, Any]],
    k_bins: int = 5,
    coverage_radius_meters: float = 300.0
) -> Dict[str, Any]:
    """
    Maximum Covering Location Problem (MCLP) Optimizer.
    Finds optimal locations for K new waste bins to maximize
    uncovered citizen demand and complaint points.
    """
    total_demand = len(demand_points)
    if total_demand == 0 or len(candidate_locations) == 0:
        return {
            "k_bins_requested": k_bins,
            "baseline_coverage_pct": 0.0,
            "optimized_coverage_pct": 0.0,
            "coverage_improvement_pct": 0.0,
            "selected_locations": []
        }

    # 1. Determine baseline coverage by existing bins
    already_covered_indices = set()
    for d_idx, dp in enumerate(demand_points):
        d_lat, d_lng = dp["latitude"], dp["longitude"]
        for eb in existing_bins:
            dist = haversine_distance_meters(d_lat, d_lng, eb["latitude"], eb["longitude"])
            if dist <= coverage_radius_meters:
                already_covered_indices.add(d_idx)
                break

    baseline_covered_count = len(already_covered_indices)
    baseline_pct = round((baseline_covered_count / total_demand) * 100, 1)

    # 2. Precompute for each candidate site which uncovered demand points it would cover
    candidate_covers = []
    for c_idx, cand in enumerate(candidate_locations):
        c_lat, c_lng = cand["latitude"], cand["longitude"]
        can_cover_demand = set()
        for d_idx, dp in enumerate(demand_points):
            dist = haversine_distance_meters(c_lat, c_lng, dp["latitude"], dp["longitude"])
            if dist <= coverage_radius_meters:
                can_cover_demand.add(d_idx)
        candidate_covers.append({
            "candidate": cand,
            "covers_all": can_cover_demand,
            "covers_uncovered": can_cover_demand - already_covered_indices
        })

    # 3. Greedy Maximum Coverage Selection for K bins
    selected_bins = []
    current_covered = set(already_covered_indices)
    remaining_candidates = list(candidate_covers)

    for rank in range(1, k_bins + 1):
        if not remaining_candidates:
            break

        # Pick candidate that maximizes marginal new coverage
        best_cand_data = None
        best_new_coverage = set()

        for cand_data in remaining_candidates:
            marginal = cand_data["covers_all"] - current_covered
            if best_cand_data is None or len(marginal) > len(best_new_coverage):
                best_cand_data = cand_data
                best_new_coverage = marginal

        if not best_cand_data or len(best_new_coverage) == 0:
            # If no marginal improvement, take the candidate with highest total coverage
            remaining_candidates.sort(key=lambda x: len(x["covers_all"]), reverse=True)
            best_cand_data = remaining_candidates[0]
            best_new_coverage = best_cand_data["covers_all"] - current_covered

        cand = best_cand_data["candidate"]
        current_covered.update(best_new_coverage)
        remaining_candidates.remove(best_cand_data)

        selected_bins.append({
            "rank": rank,
            "bin_code": f"NEW-OPT-{rank:02d}",
            "location_name": cand.get("name", f"Optimal Site #{rank}"),
            "ward_name": cand.get("ward_name", "Pune Ward"),
            "latitude": round(cand["latitude"], 6),
            "longitude": round(cand["longitude"], 6),
            "additional_points_covered": len(best_new_coverage),
            "total_points_in_radius": len(best_cand_data["covers_all"]),
            "recommended_capacity": "360L Dual Wet/Dry Solar Smart Bin",
            "priority": "High" if rank <= 2 else "Medium"
        })

    final_covered_count = len(current_covered)
    optimized_pct = round((final_covered_count / total_demand) * 100, 1)
    improvement_delta = round(optimized_pct - baseline_pct, 1)

    return {
        "k_bins_requested": k_bins,
        "coverage_radius_meters": coverage_radius_meters,
        "total_demand_nodes": total_demand,
        "baseline_covered_nodes": baseline_covered_count,
        "baseline_coverage_pct": baseline_pct,
        "final_covered_nodes": final_covered_count,
        "optimized_coverage_pct": optimized_pct,
        "coverage_improvement_pct": improvement_delta,
        "selected_locations": selected_bins,
        "algorithm": "MCLP Greedy Heuristic Optimizer"
    }
