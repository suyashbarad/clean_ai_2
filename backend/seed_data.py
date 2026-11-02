import uuid
from backend.database import get_connection

def seed_all_data():
    conn = get_connection()
    c = conn.cursor()

    # Clear existing data
    tables = [
        "complaint_timeline", "worker_tasks", "complaints", "waste_bins",
        "workers", "vouchers", "reward_transactions", "notifications",
        "hotspot_clusters", "wards", "users", "audit_logs"
    ]
    for tbl in tables:
        c.execute(f"DELETE FROM {tbl}")

    # 1. Users
    users = [
        ("u1", "Aarav Sharma", "citizen@cleangreen.in", "+91 98220 12345", "citizen", 250, "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120"),
        ("u2", "Sunita Deshmukh", "admin@pmc.gov.in", "+91 98220 54321", "admin", 100, "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=120"),
        ("u3", "Ramesh Shinde", "ramesh.worker@pmc.gov.in", "+91 98221 12233", "worker", 100, "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120"),
        ("u4", "Ganesh Jadhav", "ganesh.worker@pmc.gov.in", "+91 98224 45566", "worker", 100, "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=120"),
        ("u5", "Dr. Vikram Patil", "superadmin@pmc.gov.in", "+91 98229 99888", "superadmin", 100, "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=120")
    ]
    c.executemany("INSERT INTO users (id, name, email, phone, role, credits_balance, avatar) VALUES (?,?,?,?,?,?,?)", users)

    # 2. Wards
    wards = [
        ("W-KOT", "Kothrud - Bavdhan", "Zone 3 (West)", 18.5074, 73.8077, 18, 12, "Medium"),
        ("W-SHV", "Shivajinagar - FC Road", "Zone 1 (Central)", 18.5314, 73.8446, 24, 15, "High"),
        ("W-SWG", "Swargate - Parvati", "Zone 2 (South)", 18.5018, 73.8586, 20, 19, "Critical"),
        ("W-AUN", "Aundh - Baner", "Zone 4 (North-West)", 18.5590, 73.8055, 16, 8, "Low"),
        ("W-VMN", "Viman Nagar - Nagar Road", "Zone 5 (East)", 18.5679, 73.9143, 22, 14, "Medium"),
        ("W-HDP", "Hadapsar - Magarpatta", "Zone 6 (South-East)", 18.5089, 73.9260, 19, 11, "Medium")
    ]
    c.executemany("INSERT INTO wards (id, name, zone, center_lat, center_lng, total_bins, total_complaints, risk_level) VALUES (?,?,?,?,?,?,?,?)", wards)

    # 3. Workers
    workers = [
        ("WRK-101", "u3", "Ramesh Shinde", "+91 98221 12233", "Zone 3 (West)", "W-KOT", "Kothrud - Bavdhan", "MH 12 QX 4402", "On Duty", 2, 48, 4.9, 18.5140, 73.8180),
        ("WRK-102", "u4", "Ganesh Jadhav", "+91 98224 45566", "Zone 1 (Central)", "W-SHV", "Shivajinagar - FC Road", "MH 12 QZ 1198", "Available", 1, 37, 4.7, 18.5280, 73.8410)
    ]
    c.executemany("INSERT INTO workers (id, user_id, name, phone, zone, ward_id, ward_name, vehicle_number, status, active_tasks_count, completed_tasks_count, rating, current_lat, current_lng) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", workers)

    # 4. Waste Bins (Pune OpenStreetMap coordinates)
    bins = [
        ("BIN-PUN-01", "PMC-KB-001", "W-KOT", "Kothrud - Bavdhan", 18.5175, 73.8148, "Opposite MIT-WPU Main Gate, Paud Road", "Dual Wet/Dry Community Dustbin", 240, 45, "Normal"),
        ("BIN-PUN-02", "PMC-KB-002", "W-KOT", "Kothrud - Bavdhan", 18.5142, 73.8122, "Near Paud Phata Flyover, Karve Road", "Compactor Smart Bin", 360, 88, "Overflowing"),
        ("BIN-PUN-03", "PMC-KB-003", "W-KOT", "Kothrud - Bavdhan", 18.5098, 73.8051, "Chandani Chowk BRT Junction", "Public Litter Bin", 120, 20, "Normal"),
        ("BIN-PUN-04", "PMC-SV-001", "W-SHV", "Shivajinagar - FC Road", 18.5255, 73.8412, "Goodluck Chowk, Fergusson College Road", "Solar Smart Sensor Bin", 240, 65, "Normal"),
        ("BIN-PUN-05", "PMC-SV-002", "W-SHV", "Shivajinagar - FC Road", 18.5320, 73.8475, "Shivajinagar Metro Station Gate 2", "Public Community Dustbin", 360, 92, "Overflowing"),
        ("BIN-PUN-06", "PMC-SW-001", "W-SWG", "Swargate - Parvati", 18.5022, 73.8575, "Swargate ST Bus Stand North Gate", "Heavy Capacity Bin", 500, 95, "Full"),
        ("BIN-PUN-07", "PMC-SW-002", "W-SWG", "Swargate - Parvati", 18.4985, 73.8540, "Parvati Foothills Parking Area", "Public Litter Bin", 120, 30, "Normal"),
        ("BIN-PUN-08", "PMC-AN-001", "W-AUN", "Aundh - Baner", 18.5585, 73.8070, "Parihar Chowk, Aundh", "Dual Recyclable Bin", 240, 40, "Normal"),
        ("BIN-PUN-09", "PMC-AN-002", "W-AUN", "Aundh - Baner", 18.5612, 73.7810, "Balewadi High Street Entrance", "Underground Smart Bin", 400, 25, "Normal"),
        ("BIN-PUN-10", "PMC-VM-001", "W-VMN", "Viman Nagar - Nagar Road", 18.5670, 73.9135, "Phoenix Marketcity Frontage, Nagar Road", "Sensor Compactor Bin", 360, 70, "Normal"),
        ("BIN-PUN-11", "PMC-HD-001", "W-HDP", "Hadapsar - Magarpatta", 18.5120, 73.9310, "Magarpatta South Gate, Cybercity", "Public Community Dustbin", 240, 50, "Normal")
    ]
    c.executemany("INSERT INTO waste_bins (id, bin_code, ward_id, ward_name, latitude, longitude, address, bin_type, capacity_liters, fill_level_pct, status) VALUES (?,?,?,?,?,?,?,?,?,?,?)", bins)

    # 5. Complaints
    complaints = [
        (
            "CG-2026-1001", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1605600659908-0ef719419d41?w=600",
            "https://images.unsplash.com/photo-1605600659908-0ef719419d41?w=600",
            None,
            18.5178, 73.8151, "Paud Road pavement near MIT-WPU Gate 3, Kothrud, Pune",
            "W-KOT", "Kothrud - Bavdhan", "Zone 3 (West)", "Plastic Waste", "PET bottles & food wrappers",
            "Medium", "Assigned", 0.94, "Plastic Waste",
            "Detected single-use plastic bottles and polythene packaging accumulating along the pedestrian footpath.",
            "Dispatch dry-waste segregation unit with manual baler.",
            0, 0, "Moderate", "Piled up after weekend street food vendors.",
            "WRK-101", "Ramesh Shinde", "2026-11-01 10:15:00", None, None
        ),
        (
            "CG-2026-1002", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600",
            "https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600",
            None,
            18.5145, 73.8125, "Karve Road near Paud Phata flyover pillar #14, Kothrud",
            "W-KOT", "Kothrud - Bavdhan", "Zone 3 (West)", "Mixed Municipal Waste", "Commercial dump overflow",
            "High", "Worker En Route", 0.92, "Mixed Municipal Waste",
            "Large pile of unsegregated vegetable market waste and cardboard cartons spilling onto road curb.",
            "Deploy municipal compactor truck and mechanical sweeper immediately.",
            0, 1, "Large", "Blocking storm water drain opening.",
            "WRK-101", "Ramesh Shinde", "2026-11-01 11:30:00", None, None
        ),
        (
            "CG-2026-1003", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1528323273322-d81458248d40?w=600",
            "https://images.unsplash.com/photo-1528323273322-d81458248d40?w=600",
            "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=600",
            18.5185, 73.8160, "Rambaug Colony Lane 4, Kothrud, Pune",
            "W-KOT", "Kothrud - Bavdhan", "Zone 3 (West)", "Organic Waste", "Garden cuttings and wet food",
            "Low", "Resolved", 0.89, "Organic Waste",
            "Pruned tree branches and domestic wet waste disposed outside residential society gate.",
            "Collect and transport to nearest biomethanation plant.",
            0, 0, "Moderate", "Resolved by sanitation team.",
            "WRK-101", "Ramesh Shinde", "2026-10-31 09:00:00", "2026-10-31 14:20:00",
            "Cleared completely by Ramesh Shinde using mini-tipper MH 12 QX 4402. Disinfected with bleaching powder."
        ),
        (
            "CG-2026-1004", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600",
            "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600",
            None,
            18.5325, 73.8470, "Near Shivajinagar Railway Station backside, Pune",
            "W-SHV", "Shivajinagar - FC Road", "Zone 1 (Central)", "Construction Debris", "Concrete rubble and brick mortar",
            "High", "Assigned", 0.96, "Construction Debris",
            "Discarded construction debris blocking public passage behind auto stand.",
            "Deploy heavy hydraulic loader and designated C&D recycling carrier.",
            0, 0, "Large", "Unlawful dumping during night time.",
            "WRK-102", "Ganesh Jadhav", "2026-11-01 14:00:00", None, None
        ),
        (
            "CG-2026-1005", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?w=600",
            "https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?w=600",
            None,
            18.5020, 73.8570, "Swargate Bus Stand exit junction, Pune",
            "W-SWG", "Swargate - Parvati", "Zone 2 (South)", "Medical Waste", "Syringes, PPE gloves & chemical boxes",
            "Critical", "Verified", 0.97, "Medical Waste",
            "CRITICAL: Infectious bio-hazard materials and packaging spotted near public bus depot.",
            "CRITICAL ALERT: Emergency quarantine and bio-medical transport required immediately.",
            1, 1, "Moderate", "Emergency flag raised by AI inspection.",
            None, None, "2026-11-02 08:30:00", None, None
        ),
        (
            "CG-2026-1006", "u1", "Aarav Sharma", "+91 98220 12345",
            "https://images.unsplash.com/photo-1526951521990-620dc14c214b?w=600",
            "https://images.unsplash.com/photo-1526951521990-620dc14c214b?w=600",
            None,
            18.5028, 73.8580, "Jedhe Chowk underpass service road, Swargate",
            "W-SWG", "Swargate - Parvati", "Zone 2 (South)", "Mixed Municipal Waste", "Commercial garbage pile",
            "High", "Pending Assignment", 0.91, "Mixed Municipal Waste",
            "Repeated dumping hotspot in Swargate transit zone.",
            "Schedule night compactor clearance and CCTV surveillance.",
            0, 1, "Large", "Hotspot recurring dump.",
            None, None, "2026-11-02 09:15:00", None, None
        )
    ]
    c.executemany("""
    INSERT INTO complaints (
        id, citizen_id, citizen_name, phone, image_url, before_image_url, after_image_url,
        latitude, longitude, address, ward_id, ward_name, zone, category, subcategory,
        severity, status, ai_confidence, ai_detected_category, ai_description, ai_recommendation,
        ai_is_hazardous, ai_is_overflowing, ai_accumulation_est, notes, worker_id, worker_name,
        created_at, resolved_at, resolution_notes
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, complaints)

    # 6. Complaint Timeline
    timeline_records = [
        ("CG-2026-1001", "Submitted", "Citizen submitted complaint with photo", "Aarav Sharma", "2026-11-01 10:15:00"),
        ("CG-2026-1001", "Verified", "AI model verified Plastic Waste (94% confidence)", "AI Vision Core", "2026-11-01 10:16:00"),
        ("CG-2026-1001", "Assigned", "Assigned to Ramesh Shinde (Zone 3)", "Sunita Deshmukh", "2026-11-01 10:45:00"),

        ("CG-2026-1002", "Submitted", "Citizen submitted complaint with photo", "Aarav Sharma", "2026-11-01 11:30:00"),
        ("CG-2026-1002", "Verified", "High severity detected (Drain blockage risk)", "AI Vision Core", "2026-11-01 11:31:00"),
        ("CG-2026-1002", "Assigned", "Assigned to Ramesh Shinde", "Sunita Deshmukh", "2026-11-01 11:45:00"),
        ("CG-2026-1002", "Worker En Route", "Worker dispatched with compactor MH 12 QX 4402", "Ramesh Shinde", "2026-11-01 12:10:00"),

        ("CG-2026-1003", "Submitted", "Citizen submitted garden waste photo", "Aarav Sharma", "2026-10-31 09:00:00"),
        ("CG-2026-1003", "Verified", "Organic waste classified", "AI Vision Core", "2026-10-31 09:02:00"),
        ("CG-2026-1003", "Assigned", "Assigned to Ramesh Shinde", "Sunita Deshmukh", "2026-10-31 10:00:00"),
        ("CG-2026-1003", "Cleanup in Progress", "Sanitation worker on site", "Ramesh Shinde", "2026-10-31 13:00:00"),
        ("CG-2026-1003", "Resolved", "Site cleaned and disinfected. 50 Green Credits awarded.", "Ramesh Shinde", "2026-10-31 14:20:00")
    ]
    c.executemany("INSERT INTO complaint_timeline (complaint_id, status, notes, updated_by, timestamp) VALUES (?,?,?,?,?)", timeline_records)

    # 7. Worker Tasks
    tasks = [
        ("TSK-01", "WRK-101", "CG-2026-1002", "High", 1, "En Route", "2026-11-01 11:45:00", None, "En route to Karve road flyover", None),
        ("TSK-02", "WRK-101", "CG-2026-1001", "Medium", 2, "Assigned", "2026-11-01 10:45:00", None, "Pending completion of TSK-01", None),
        ("TSK-03", "WRK-102", "CG-2026-1004", "High", 1, "Assigned", "2026-11-01 14:00:00", None, "Requires hydraulic loader truck", None)
    ]
    c.executemany("INSERT INTO worker_tasks (id, worker_id, complaint_id, priority, sequence_order, status, assigned_at, completed_at, cleanup_notes, after_photo_url) VALUES (?,?,?,?,?,?,?,?,?,?)", tasks)

    # 8. Reward Transactions & Pune Vouchers
    reward_txns = [
        ("TXN-101", "u1", 50, "CREDIT", "Initial Welcome Bonus for joining CleanGreen AI Pune", None, "2026-10-30 08:00:00"),
        ("TXN-102", "u1", 100, "CREDIT", "Verified waste report for Rambaug Colony (CG-2026-1003)", "CG-2026-1003", "2026-10-31 14:20:00"),
        ("TXN-103", "u1", 50, "CREDIT", "Verified complaint submission for Paud Road (CG-2026-1001)", "CG-2026-1001", "2026-11-01 10:15:00"),
        ("TXN-104", "u1", 50, "CREDIT", "Verified high-severity report for Karve Road (CG-2026-1002)", "CG-2026-1002", "2026-11-01 11:30:00")
    ]
    c.executemany("INSERT INTO reward_transactions (id, user_id, amount, transaction_type, reason, complaint_id, created_at) VALUES (?,?,?,?,?,?,?)", reward_txns)

    vouchers = [
        (
            "VCH-METRO-01", "u1", "PUN-METRO-50-AARAV", "MahaMetro Pune",
            "MahaMetro ₹25 Fare Pass Voucher",
            "Valid for any single journey across Line 1 (PCMC-Swargate) or Line 2 (Vanaz-Ramwadi).",
            100, "Active", "PUN-METRO-QR-AUTH-2026-1001", "2026-10-31 15:00:00", "2026-12-31 23:59:59"
        )
    ]
    c.executemany("INSERT INTO vouchers (id, user_id, code, partner_name, title, benefit, cost_credits, status, qr_code_data, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", vouchers)

    # 9. Notifications
    notifs = [
        ("N-01", "u1", "Complaint Verified!", "Your report CG-2026-1001 was verified by AI. +50 Green Credits earned!", "reward", 0, "2026-11-01 10:16:00"),
        ("N-02", "u1", "Sanitation Worker Assigned", "Worker Ramesh Shinde has been assigned to your complaint CG-2026-1002.", "worker", 0, "2026-11-01 11:45:00"),
        ("N-03", "u1", "Complaint CG-2026-1003 Resolved", "Cleanup is completed! Before and after photos verified.", "success", 1, "2026-10-31 14:20:00")
    ]
    c.executemany("INSERT INTO notifications (id, user_id, title, message, notification_type, is_read, created_at) VALUES (?,?,?,?,?,?,?)", notifs)

    conn.commit()
    conn.close()
    print("Seed data successfully populated.")

if __name__ == "__main__":
    seed_all_data()
