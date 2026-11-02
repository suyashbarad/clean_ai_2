import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
from backend.database import get_connection
from backend.config import UPLOAD_DIR
from backend.ml.dbscan_service import haversine_distance_meters

router = APIRouter(prefix="/api/workers", tags=["Workers"])

@router.get("")
def list_workers():
    conn = get_connection()
    c = conn.cursor()
    workers = c.execute("SELECT * FROM workers ORDER BY rating DESC").fetchall()
    conn.close()
    return {"workers": [dict(w) for w in workers]}

@router.get("/{worker_id}/tasks")
def get_worker_tasks(worker_id: str):
    conn = get_connection()
    c = conn.cursor()

    worker = c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if not worker:
        conn.close()
        raise HTTPException(status_code=404, detail="Worker not found")

    tasks = c.execute("""
        SELECT wt.*, c.address, c.latitude, c.longitude, c.category, c.severity,
               c.ai_recommendation, c.image_url as complaint_image, c.status as complaint_status
        FROM worker_tasks wt
        JOIN complaints c ON wt.complaint_id = c.id
        WHERE wt.worker_id = ? AND wt.status != 'Completed'
        ORDER BY wt.sequence_order ASC
    """, (worker_id,)).fetchall()

    completed_tasks = c.execute("""
        SELECT wt.*, c.address, c.latitude, c.longitude, c.category, c.severity,
               c.image_url as complaint_image
        FROM worker_tasks wt
        JOIN complaints c ON wt.complaint_id = c.id
        WHERE wt.worker_id = ? AND wt.status = 'Completed'
        ORDER BY wt.completed_at DESC
        LIMIT 10
    """, (worker_id,)).fetchall()

    conn.close()
    return {
        "worker": dict(worker),
        "active_tasks": [dict(t) for t in tasks],
        "completed_tasks": [dict(t) for t in completed_tasks]
    }

@router.post("/{worker_id}/optimize-route")
def optimize_route(worker_id: str):
    """
    Route optimization using Traveling Salesperson Problem (TSP) Nearest Neighbor.
    Orders tasks so the worker travels the minimum cumulative distance starting from their current position.
    """
    conn = get_connection()
    c = conn.cursor()

    worker = c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if not worker:
        conn.close()
        raise HTTPException(status_code=404, detail="Worker not found")

    start_lat = worker["current_lat"] or 18.5140
    start_lng = worker["current_lng"] or 73.8180

    tasks = c.execute("""
        SELECT wt.id, wt.complaint_id, c.latitude, c.longitude, c.address, c.severity
        FROM worker_tasks wt
        JOIN complaints c ON wt.complaint_id = c.id
        WHERE wt.worker_id = ? AND wt.status != 'Completed'
    """, (worker_id,)).fetchall()

    task_list = [dict(t) for t in tasks]
    if len(task_list) <= 1:
        conn.close()
        return {"success": True, "message": "Route already optimal.", "tasks": task_list}

    # Nearest Neighbor Greedy TSP
    unvisited = list(task_list)
    ordered_tasks = []
    current_lat, current_lng = start_lat, start_lng
    total_distance_km = 0.0

    while unvisited:
        nearest = None
        min_dist = float('inf')
        for item in unvisited:
            dist = haversine_distance_meters(current_lat, current_lng, item["latitude"], item["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest = item

        ordered_tasks.append(nearest)
        unvisited.remove(nearest)
        total_distance_km += (min_dist / 1000.0)
        current_lat, current_lng = nearest["latitude"], nearest["longitude"]

    # Update sequence_order in database
    for seq, t in enumerate(ordered_tasks, 1):
        c.execute("UPDATE worker_tasks SET sequence_order = ? WHERE id = ?", (seq, t["id"]))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "total_distance_km": round(total_distance_km, 2),
        "optimized_count": len(ordered_tasks),
        "tasks": ordered_tasks
    }

@router.post("/{worker_id}/tasks/{task_id}/resolve")
async def resolve_task(
    worker_id: str,
    task_id: str,
    cleanup_notes: str = Form("Area swept, waste loaded into mini-tipper, disinfectant sprayed."),
    after_photo: Optional[UploadFile] = File(None)
):
    conn = get_connection()
    c = conn.cursor()

    task = c.execute("SELECT * FROM worker_tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    complaint_id = task["complaint_id"]

    after_photo_url = "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=600"
    if after_photo:
        contents = await after_photo.read()
        filename = f"after_{complaint_id}_{after_photo.filename}"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(contents)
        after_photo_url = f"/uploads/{filename}"

    # Update Task
    c.execute("""
        UPDATE worker_tasks
        SET status = 'Completed', completed_at = CURRENT_TIMESTAMP,
            cleanup_notes = ?, after_photo_url = ?
        WHERE id = ?
    """, (cleanup_notes, after_photo_url, task_id))

    # Update Complaint
    c.execute("""
        UPDATE complaints
        SET status = 'Resolved', resolved_at = CURRENT_TIMESTAMP,
            after_image_url = ?, resolution_notes = ?
        WHERE id = ?
    """, (after_photo_url, cleanup_notes, complaint_id))

    # Update Worker stats
    c.execute("""
        UPDATE workers
        SET active_tasks_count = MAX(0, active_tasks_count - 1),
            completed_tasks_count = completed_tasks_count + 1
        WHERE id = ?
    """, (worker_id,))

    # Add timeline record
    worker = c.execute("SELECT name FROM workers WHERE id = ?", (worker_id,)).fetchone()
    worker_name = worker["name"] if worker else "Sanitation Worker"
    c.execute("""
        INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by)
        VALUES (?, 'Resolved', ?, ?)
    """, (complaint_id, f"Resolved by {worker_name}. {cleanup_notes}", worker_name))

    # Award bonus resolution credits to citizen
    complaint = c.execute("SELECT citizen_id FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if complaint and complaint["citizen_id"]:
        c.execute("UPDATE users SET credits_balance = credits_balance + 25 WHERE id = ?", (complaint["citizen_id"],))
        c.execute("""
            INSERT INTO reward_transactions (id, user_id, amount, transaction_type, reason, complaint_id)
            VALUES (?, ?, 25, 'CREDIT', ?, ?)
        """, (f"TXN-{uuid.uuid4().hex[:6].upper()}", complaint["citizen_id"], f"Resolution bonus for {complaint_id}", complaint_id))
        c.execute("""
            INSERT INTO notifications (id, user_id, title, message, notification_type)
            VALUES (?, ?, 'Cleanup Completed!', ?, 'success')
        """, (f"N-{uuid.uuid4().hex[:6].upper()}", complaint["citizen_id"], f"Cleanup for complaint {complaint_id} is completed! +25 bonus credits added."))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Task {task_id} marked as Completed. Complaint {complaint_id} resolved.",
        "after_photo_url": after_photo_url
    }
