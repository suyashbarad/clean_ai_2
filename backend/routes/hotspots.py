import uuid
from fastapi import APIRouter
from backend.database import get_connection
from backend.ml.dbscan_service import run_dbscan_clustering

router = APIRouter(prefix="/api/hotspots", tags=["Hotspots"])

@router.get("")
def get_hotspots(eps_meters: float = 350.0, min_samples: int = 2):
    conn = get_connection()
    c = conn.cursor()

    complaints = c.execute("SELECT * FROM complaints").fetchall()
    complaints_data = [dict(r) for r in complaints]

    # Run DBSCAN
    clustering_result = run_dbscan_clustering(complaints_data, eps_meters=eps_meters, min_samples=min_samples)

    # Cache clusters in DB
    c.execute("DELETE FROM hotspot_clusters")
    for cl in clustering_result["clusters"]:
        cluster_id = f"HOT-{cl['cluster_id']}-{uuid.uuid4().hex[:4].upper()}"
        c.execute("""
            INSERT INTO hotspot_clusters (
                id, ward_name, center_lat, center_lng, radius_meters,
                complaint_count, severity_score, risk_tier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cluster_id, cl["ward_name"], cl["center_lat"], cl["center_lng"],
            cl["radius_meters"], cl["complaint_count"], cl["severity_score"], cl["risk_tier"]
        ))

    conn.commit()

    # Ward-level risk summary
    ward_stats = c.execute("""
        SELECT ward_name,
               COUNT(*) as total_reports,
               SUM(CASE WHEN severity IN ('High', 'Critical') THEN 1 ELSE 0 END) as high_risk_count,
               SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END) as pending_count
        FROM complaints
        GROUP BY ward_name
        ORDER BY high_risk_count DESC
    """).fetchall()

    conn.close()

    return {
        **clustering_result,
        "ward_risk_distribution": [dict(w) for w in ward_stats]
    }
