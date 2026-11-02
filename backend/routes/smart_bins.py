from fastapi import APIRouter, Query, Form
from typing import Optional
from backend.database import get_connection
from backend.ml.mclp_service import solve_mclp

router = APIRouter(prefix="/api/smart-bins", tags=["Smart Bins"])

# Pune prospective candidate sites for new smart bins
CANDIDATE_SITES = [
    {"name": "Cummins College Road Junction", "ward_name": "Kothrud - Bavdhan", "latitude": 18.4905, "longitude": 73.8188},
    {"name": "Garware College Metro Interchange", "ward_name": "Kothrud - Bavdhan", "latitude": 18.5122, "longitude": 73.8340},
    {"name": "Deccan Gymkhana Bus Terminal", "ward_name": "Shivajinagar - FC Road", "latitude": 18.5165, "longitude": 73.8405},
    {"name": "Pune University Circle / SPPU Gate", "ward_name": "Shivajinagar - FC Road", "latitude": 18.5412, "longitude": 73.8290},
    {"name": "Sarasbaug Ganesh Temple Frontage", "ward_name": "Swargate - Parvati", "latitude": 18.5020, "longitude": 73.8525},
    {"name": "Mitramandal Chowk, Parvati", "ward_name": "Swargate - Parvati", "latitude": 18.4940, "longitude": 73.8560},
    {"name": "Westend Mall Entrance, Aundh", "ward_name": "Aundh - Baner", "latitude": 18.5620, "longitude": 73.8080},
    {"name": "Balewadi Phata High Street", "ward_name": "Aundh - Baner", "latitude": 18.5680, "longitude": 73.7790},
    {"name": "Symbiosis International Campus Road", "ward_name": "Viman Nagar - Nagar Road", "latitude": 18.5710, "longitude": 73.9080},
    {"name": "Hadapsar Gadital Bus Depot", "ward_name": "Hadapsar - Magarpatta", "latitude": 18.5015, "longitude": 73.9350}
]

@router.get("")
def list_bins(status: Optional[str] = None, ward_id: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM waste_bins WHERE 1=1"
    params = []

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    if ward_id and ward_id != "All":
        query += " AND ward_id = ?"
        params.append(ward_id)

    query += " ORDER BY fill_level_pct DESC"
    bins = c.execute(query, params).fetchall()
    conn.close()

    return {"bins": [dict(b) for b in bins], "count": len(bins)}

@router.post("/optimize")
def optimize_bin_placement(
    k_bins: int = Form(4),
    coverage_radius_meters: float = Form(350.0)
):
    """
    Solves MCLP optimization using actual complaint demand locations and existing dustbins in Pune.
    """
    conn = get_connection()
    c = conn.cursor()

    existing_bins = [dict(b) for b in c.execute("SELECT latitude, longitude, bin_code FROM waste_bins").fetchall()]
    complaints = [dict(r) for r in c.execute("SELECT latitude, longitude, id FROM complaints").fetchall()]

    conn.close()

    result = solve_mclp(
        existing_bins=existing_bins,
        demand_points=complaints,
        candidate_locations=CANDIDATE_SITES,
        k_bins=k_bins,
        coverage_radius_meters=coverage_radius_meters
    )

    return result
