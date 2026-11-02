import math
import numpy as np
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any

EARTH_RADIUS_METERS = 6371000.0

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c

def run_dbscan_clustering(
    complaints: List[Dict[str, Any]],
    eps_meters: float = 350.0,
    min_samples: int = 2
) -> Dict[str, Any]:
    """
    Executes DBSCAN spatial clustering on real geo-coordinates of waste complaints.
    Returns detected hotspot clusters, metrics, and predictive risk scoring.
    """
    if len(complaints) < min_samples:
        return {
            "total_complaints": len(complaints),
            "clusters_found": 0,
            "clusters": [],
            "noise_points_count": len(complaints),
            "summary": "Insufficient complaints to form spatial clusters."
        }

    coords = np.array([[c["latitude"], c["longitude"]] for c in complaints])
    # Convert lat/long degrees to radians for Haversine metric
    coords_rad = np.radians(coords)
    eps_rad = eps_meters / EARTH_RADIUS_METERS

    db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric='haversine')
    labels = db.fit_predict(coords_rad)

    unique_labels = set(labels)
    clusters = []
    noise_count = int(np.sum(labels == -1))

    for label in unique_labels:
        if label == -1:
            continue
        cluster_mask = (labels == label)
        cluster_coords = coords[cluster_mask]
        cluster_complaints = [complaints[i] for i, m in enumerate(cluster_mask) if m]

        # Calculate centroid
        center_lat = float(np.mean(cluster_coords[:, 0]))
        center_lng = float(np.mean(cluster_coords[:, 1]))

        # Calculate radius in meters from centroid to furthest member
        max_dist = max(
            haversine_distance_meters(center_lat, center_lng, pt[0], pt[1])
            for pt in cluster_coords
        )
        radius = max(round(max_dist, 1), 75.0)

        # Count critical & high severity complaints
        high_critical_count = sum(
            1 for c in cluster_complaints if c.get("severity") in ["High", "Critical"]
        )
        total_in_cluster = len(cluster_complaints)
        severity_ratio = high_critical_count / total_in_cluster if total_in_cluster else 0

        # Predictive hotspot score (0 - 100)
        # Based on complaint count, severity density, and unresolved status
        unresolved_count = sum(1 for c in cluster_complaints if c.get("status") not in ["Resolved", "Rejected"])
        score = min(100.0, round(
            (total_in_cluster * 12.0) + (severity_ratio * 40.0) + (unresolved_count * 15.0),
            1
        ))

        if score >= 75.0:
            risk_tier = "Critical"
        elif score >= 50.0:
            risk_tier = "High"
        elif score >= 25.0:
            risk_tier = "Medium"
        else:
            risk_tier = "Low"

        # Determine prominent ward
        ward_names = [c.get("ward_name") for c in cluster_complaints if c.get("ward_name")]
        prominent_ward = max(set(ward_names), key=ward_names.count) if ward_names else "Pune Central"

        clusters.append({
            "cluster_id": int(label),
            "ward_name": prominent_ward,
            "center_lat": round(center_lat, 6),
            "center_lng": round(center_lng, 6),
            "radius_meters": radius,
            "complaint_count": total_in_cluster,
            "unresolved_count": unresolved_count,
            "severity_score": score,
            "risk_tier": risk_tier,
            "recommended_action": f"Deploy daily proactive sweep and assign rapid response crew to {prominent_ward} hotspot.",
            "complaint_ids": [c.get("id") for c in cluster_complaints]
        })

    # Sort by severity score descending
    clusters.sort(key=lambda x: x["severity_score"], reverse=True)

    return {
        "total_complaints_analyzed": len(complaints),
        "clusters_found": len(clusters),
        "noise_points_count": noise_count,
        "clusters": clusters,
        "high_risk_hotspots": len([c for c in clusters if c["risk_tier"] in ["High", "Critical"]]),
        "algorithm": "DBSCAN (Haversine distance)",
        "parameters": {"eps_meters": eps_meters, "min_samples": min_samples}
    }
