import sqlite3
import json
from pathlib import Path
from backend.config import BASE_DIR

DB_PATH = BASE_DIR / "cleangreen.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        role TEXT NOT NULL DEFAULT 'citizen',
        credits_balance INTEGER DEFAULT 100,
        avatar TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS wards (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        zone TEXT NOT NULL,
        center_lat REAL NOT NULL,
        center_lng REAL NOT NULL,
        total_bins INTEGER DEFAULT 0,
        total_complaints INTEGER DEFAULT 0,
        risk_level TEXT DEFAULT 'Low'
    );

    CREATE TABLE IF NOT EXISTS waste_bins (
        id TEXT PRIMARY KEY,
        bin_code TEXT UNIQUE NOT NULL,
        ward_id TEXT NOT NULL,
        ward_name TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        bin_type TEXT DEFAULT 'Public Community Dustbin',
        capacity_liters INTEGER DEFAULT 240,
        fill_level_pct INTEGER DEFAULT 35,
        status TEXT DEFAULT 'Normal',
        last_emptied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS complaints (
        id TEXT PRIMARY KEY,
        citizen_id TEXT NOT NULL,
        citizen_name TEXT,
        phone TEXT,
        image_url TEXT,
        before_image_url TEXT,
        after_image_url TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        ward_id TEXT,
        ward_name TEXT,
        zone TEXT,
        category TEXT NOT NULL,
        subcategory TEXT,
        severity TEXT NOT NULL DEFAULT 'Medium',
        status TEXT NOT NULL DEFAULT 'Submitted',
        ai_confidence REAL DEFAULT 0.0,
        ai_detected_category TEXT,
        ai_description TEXT,
        ai_recommendation TEXT,
        ai_is_hazardous INTEGER DEFAULT 0,
        ai_is_overflowing INTEGER DEFAULT 0,
        ai_accumulation_est TEXT DEFAULT 'Moderate',
        notes TEXT,
        worker_id TEXT,
        worker_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution_notes TEXT
    );

    CREATE TABLE IF NOT EXISTS complaint_timeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        status TEXT NOT NULL,
        notes TEXT,
        updated_by TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        name TEXT NOT NULL,
        phone TEXT,
        zone TEXT NOT NULL,
        ward_id TEXT,
        ward_name TEXT,
        vehicle_number TEXT,
        status TEXT DEFAULT 'Available',
        active_tasks_count INTEGER DEFAULT 0,
        completed_tasks_count INTEGER DEFAULT 0,
        rating REAL DEFAULT 4.8,
        current_lat REAL,
        current_lng REAL
    );

    CREATE TABLE IF NOT EXISTS worker_tasks (
        id TEXT PRIMARY KEY,
        worker_id TEXT NOT NULL,
        complaint_id TEXT NOT NULL,
        priority TEXT DEFAULT 'Medium',
        sequence_order INTEGER DEFAULT 1,
        status TEXT DEFAULT 'Assigned',
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        cleanup_notes TEXT,
        after_photo_url TEXT,
        FOREIGN KEY(worker_id) REFERENCES workers(id),
        FOREIGN KEY(complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hotspot_clusters (
        id TEXT PRIMARY KEY,
        ward_id TEXT,
        ward_name TEXT,
        center_lat REAL NOT NULL,
        center_lng REAL NOT NULL,
        radius_meters REAL DEFAULT 250.0,
        complaint_count INTEGER DEFAULT 0,
        severity_score REAL DEFAULT 0.0,
        risk_tier TEXT DEFAULT 'Medium',
        last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS reward_transactions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        reason TEXT NOT NULL,
        complaint_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS vouchers (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        partner_name TEXT NOT NULL,
        title TEXT NOT NULL,
        benefit TEXT NOT NULL,
        cost_credits INTEGER NOT NULL,
        status TEXT DEFAULT 'Active',
        qr_code_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
