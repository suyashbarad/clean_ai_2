import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional, List
from backend.database import get_connection
from backend.config import UPLOAD_DIR
from backend.ml.vision_service import analyze_waste_image

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

@router.get("")
def list_complaints(
    status: Optional[str] = None,
    ward_id: Optional[str] = None,
    severity: Optional[str] = None,
    citizen_id: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM complaints WHERE 1=1"
    params = []

    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    if ward_id and ward_id != "All":
        query += " AND ward_id = ?"
        params.append(ward_id)
    if severity and severity != "All":
        query += " AND severity = ?"
        params.append(severity)
    if citizen_id:
        query += " AND citizen_id = ?"
        params.append(citizen_id)
    if search:
        query += " AND (address LIKE ? OR notes LIKE ? OR category LIKE ? OR id LIKE ?)"
        wild = f"%{search}%"
        params.extend([wild, wild, wild, wild])

    query += " ORDER BY created_at DESC"
    rows = c.execute(query, params).fetchall()
    complaints = [dict(r) for r in rows]
    conn.close()
    return {"complaints": complaints, "count": len(complaints)}

@router.get("/{complaint_id}")
def get_complaint(complaint_id: str):
    conn = get_connection()
    c = conn.cursor()

    complaint = c.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")

    timeline = c.execute("SELECT * FROM complaint_timeline WHERE complaint_id = ? ORDER BY timestamp ASC", (complaint_id,)).fetchall()
    conn.close()

    comp_dict = dict(complaint)
    forensic = analyze_waste_image(b"", filename=comp_dict.get("category", ""), user_notes=comp_dict.get("notes", ""))

    return {
        "complaint": comp_dict,
        "timeline": [dict(t) for t in timeline],
        "forensic_report": forensic
    }

@router.delete("/{complaint_id}")
def delete_complaint(complaint_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM complaint_timeline WHERE complaint_id = ?", (complaint_id,))
    c.execute("DELETE FROM worker_tasks WHERE complaint_id = ?", (complaint_id,))
    c.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Complaint {complaint_id} deleted."}

@router.post("/analyze-preview")
async def preview_ai_analysis(
    photo: UploadFile = File(...),
    notes: Optional[str] = Form("")
):
    contents = await photo.read()
    analysis = analyze_waste_image(contents, filename=photo.filename, user_notes=notes)
    return {"analysis": analysis}

@router.post("")
async def create_complaint(
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form("MIT-WPU Paud Road, Pune"),
    category: str = Form("Mixed Municipal Waste"),
    notes: Optional[str] = Form(""),
    citizen_name: Optional[str] = Form("Aarav Sharma"),
    citizen_phone: Optional[str] = Form("+91 98220 12345"),
    ward_id: Optional[str] = Form("W-KOT"),
    photo: Optional[UploadFile] = File(None)
):
    conn = get_connection()
    c = conn.cursor()

    complaint_id = f"CG-2026-{uuid.uuid4().hex[:4].upper()}"

    # Handle image upload
    image_url = "https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600"
    image_bytes = b""
    if photo:
        image_bytes = await photo.read()
        filename = f"{complaint_id}_{photo.filename}"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        image_url = f"/uploads/{filename}"

    # Run AI Vision Analysis
    ai_result = analyze_waste_image(image_bytes, filename=photo.filename if photo else "", user_notes=notes)

    # Ward resolution
    ward_row = c.execute("SELECT name, zone FROM wards WHERE id = ?", (ward_id,)).fetchone()
    ward_name = ward_row["name"] if ward_row else "Kothrud - Bavdhan"
    zone = ward_row["zone"] if ward_row else "Zone 3 (West)"

    c.execute("""
    INSERT INTO complaints (
        id, citizen_id, citizen_name, phone, image_url, before_image_url,
        latitude, longitude, address, ward_id, ward_name, zone, category, subcategory,
        severity, status, ai_confidence, ai_detected_category, ai_description, ai_recommendation,
        ai_is_hazardous, ai_is_overflowing, ai_accumulation_est, notes, created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
    """, (
        complaint_id, "u1", citizen_name, citizen_phone, image_url, image_url,
        latitude, longitude, address, ward_id, ward_name, zone,
        category or ai_result["primary_category"], ai_result["subcategory"],
        ai_result["severity"], "Verified", ai_result["confidence"],
        ai_result["primary_category"], ai_result["description"], ai_result["recommended_action"],
        1 if ai_result["is_hazardous"] else 0,
        1 if ai_result["is_overflowing"] else 0,
        ai_result["accumulation_estimate"], notes
    ))

    # Add initial timeline events
    c.execute("INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by) VALUES (?,?,?,?)",
              (complaint_id, "Submitted", "Citizen submitted complaint with photograph & GPS pin.", citizen_name))
    c.execute("INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by) VALUES (?,?,?,?)",
              (complaint_id, "Verified", f"AI Vision classified as {ai_result['primary_category']} ({int(ai_result['confidence']*100)}% confidence).", "AI Vision Engine"))

    # Award Green Credits to citizen
    c.execute("UPDATE users SET credits_balance = credits_balance + 50 WHERE id = 'u1'")
    c.execute("""
    INSERT INTO reward_transactions (id, user_id, amount, transaction_type, reason, complaint_id)
    VALUES (?, 'u1', 50, 'CREDIT', ?, ?)
    """, (f"TXN-{uuid.uuid4().hex[:6].upper()}", f"Award for complaint report #{complaint_id}", complaint_id))

    # Create notification
    c.execute("""
    INSERT INTO notifications (id, user_id, title, message, notification_type)
    VALUES (?, 'u1', 'Report Verified & Credits Earned!', ?, 'reward')
    """, (f"N-{uuid.uuid4().hex[:6].upper()}", f"Your complaint {complaint_id} was verified. +50 Green Credits added to your wallet!"))

    conn.commit()

    created = c.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    conn.close()

    return {
        "success": True,
        "complaint": dict(created),
        "ai_analysis": ai_result,
        "credits_awarded": 50,
        "message": f"Complaint {complaint_id} successfully registered and verified."
    }

@router.post("/{complaint_id}/assign")
def assign_worker(complaint_id: str, worker_id: str = Form(...)):
    conn = get_connection()
    c = conn.cursor()

    worker = c.execute("SELECT * FROM workers WHERE id = ?", (worker_id,)).fetchone()
    if not worker:
        conn.close()
        raise HTTPException(status_code=404, detail="Worker not found")

    c.execute("""
        UPDATE complaints
        SET status = 'Assigned', worker_id = ?, worker_name = ?
        WHERE id = ?
    """, (worker["id"], worker["name"], complaint_id))

    # Add to worker tasks
    task_id = f"TSK-{uuid.uuid4().hex[:4].upper()}"
    c.execute("""
    INSERT INTO worker_tasks (id, worker_id, complaint_id, priority, status)
    VALUES (?, ?, ?, 'High', 'Assigned')
    """, (task_id, worker["id"], complaint_id))

    c.execute("UPDATE workers SET active_tasks_count = active_tasks_count + 1 WHERE id = ?", (worker["id"],))

    c.execute("""
    INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by)
    VALUES (?, 'Assigned', ?, 'Municipal Administrator')
    """, (complaint_id, f"Assigned to sanitation worker {worker['name']} ({worker['zone']})"))

    conn.commit()
    conn.close()
    return {"success": True, "message": f"Assigned {complaint_id} to {worker['name']}"}

@router.patch("/{complaint_id}/status")
def update_status(complaint_id: str, new_status: str = Form(...), notes: Optional[str] = Form("")):
    conn = get_connection()
    c = conn.cursor()

    c.execute("UPDATE complaints SET status = ? WHERE id = ?", (new_status, complaint_id))
    c.execute("""
    INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by)
    VALUES (?, ?, ?, 'System Admin')
    """, (complaint_id, new_status, notes or f"Status changed to {new_status}"))

    conn.commit()
    conn.close()
    return {"success": True, "status": new_status}
