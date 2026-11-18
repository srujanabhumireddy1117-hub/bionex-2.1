import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_NAME = "bionex.db"


def hash_password(password: str, salt: str = "bionex_salt_2026") -> str:
    """Deterministic salted SHA-256 hash for secure academic deployment."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs("static", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    
    with get_connection() as conn:
        # Check if users table needs migration (old schema had no email column)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        if table_exists:
            col_info = conn.execute("PRAGMA table_info(users)").fetchall()
            col_names = [c["name"] for c in col_info]
            if "email" not in col_names:
                # Drop old incompatible tables to allow fresh clean schema
                conn.executescript("""
                    DROP TABLE IF EXISTS users;
                    DROP TABLE IF EXISTS collection_requests;
                    DROP TABLE IF EXISTS waste_records;
                    DROP TABLE IF EXISTS bins;
                    DROP TABLE IF EXISTS bin_status;
                    DROP TABLE IF EXISTS alerts;
                    DROP TABLE IF EXISTS robot_state;
                    DROP TABLE IF EXISTS robots;
                    DROP TABLE IF EXISTS rooms;
                    DROP TABLE IF EXISTS robot_logs;
                    DROP TABLE IF EXISTS delivery_records;
                    DROP TABLE IF EXISTS uploaded_documents;
                    DROP TABLE IF EXISTS audit_logs;
                """)

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'User', -- 'Admin' or 'User'
            department TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building TEXT NOT NULL,
            floor TEXT NOT NULL,
            room_number TEXT NOT NULL,
            ward_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS robots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active / Ready',
            battery_percent INTEGER NOT NULL DEFAULT 100,
            current_location TEXT NOT NULL DEFAULT 'Dock Station',
            current_task TEXT NOT NULL DEFAULT 'Standby',
            is_charging INTEGER NOT NULL DEFAULT 0,
            e_stop_active INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS collection_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            building TEXT NOT NULL DEFAULT 'Main Block',
            floor TEXT NOT NULL DEFAULT '1st Floor',
            requested_by TEXT NOT NULL,
            item_description TEXT NOT NULL,
            category TEXT NOT NULL, -- Yellow, Red, White, Blue, Human Review
            priority TEXT NOT NULL DEFAULT 'Normal', -- Normal, High, Emergency
            status TEXT NOT NULL DEFAULT 'Pending', -- Pending, Assigned, In Progress, Completed, Human Review, Cancelled
            assigned_robot_id INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(assigned_robot_id) REFERENCES robots(id)
        );

        CREATE TABLE IF NOT EXISTS waste_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            robot_id INTEGER DEFAULT 1,
            room TEXT NOT NULL,
            category TEXT NOT NULL,
            item_description TEXT NOT NULL,
            measured_weight_grams REAL DEFAULT 150.0,
            deposit_verified INTEGER NOT NULL DEFAULT 1,
            collected_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES collection_requests(id),
            FOREIGN KEY(robot_id) REFERENCES robots(id)
        );

        CREATE TABLE IF NOT EXISTS bin_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id INTEGER NOT NULL DEFAULT 1,
            category TEXT NOT NULL, -- Yellow, Red, White, Blue
            fill_percent INTEGER NOT NULL DEFAULT 0,
            capacity_percent INTEGER NOT NULL DEFAULT 100,
            current_weight_grams REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL,
            UNIQUE(robot_id, category)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id INTEGER DEFAULT 1,
            type TEXT NOT NULL DEFAULT 'system',
            severity TEXT NOT NULL DEFAULT 'info', -- info, warning, danger
            message TEXT NOT NULL,
            is_resolved INTEGER NOT NULL DEFAULT 0,
            resolved_by TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE TABLE IF NOT EXISTS robot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id INTEGER NOT NULL DEFAULT 1,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS delivery_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manifest_code TEXT UNIQUE NOT NULL,
            facility_name TEXT NOT NULL,
            vehicle_number TEXT NOT NULL,
            total_weight_kg REAL NOT NULL,
            category_breakdown TEXT NOT NULL, -- JSON string
            handover_time TEXT NOT NULL,
            staff_signature TEXT NOT NULL,
            acknowledgement_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS uploaded_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL DEFAULT 'PDF',
            chunk_count INTEGER NOT NULL DEFAULT 0,
            file_size_kb REAL NOT NULL DEFAULT 0.0,
            uploaded_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            resource TEXT NOT NULL,
            ip_address TEXT NOT NULL DEFAULT '127.0.0.1',
            timestamp TEXT NOT NULL
        );
        """)

        now = datetime.now().isoformat(timespec="seconds")

        # 1. Seed Default Users
        user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if user_count == 0:
            default_users = [
                ("admin@bionex.hospital", hash_password("admin123"), "Dr. Ramesh Gupta", "Admin", "Infection Control Command"),
                ("nurse.sarah@bionex.hospital", hash_password("nurse123"), "Nurse Sarah Jenkins", "User", "General Ward A"),
                ("nurse.priya@bionex.hospital", hash_password("nurse123"), "Nurse Priya Patel", "User", "Intensive Care Unit (ICU)"),
                ("dr.vikram@bionex.hospital", hash_password("doctor123"), "Dr. Vikram Sharma", "User", "Emergency Trauma Center"),
                ("tech.maya@bionex.hospital", hash_password("tech123"), "Technician Maya Sen", "User", "Central Pathology Lab"),
            ]
            for email, p_hash, name, role, dept in default_users:
                conn.execute(
                    """INSERT INTO users(email, password_hash, name, role, department, is_active, created_at)
                       VALUES (?, ?, ?, ?, ?, 1, ?)""",
                    (email, p_hash, name, role, dept, now)
                )

        # 2. Seed Default Rooms
        room_count = conn.execute("SELECT COUNT(*) AS c FROM rooms").fetchone()["c"]
        if room_count == 0:
            default_rooms = [
                ("Main Block", "1st Floor", "Ward A - Rm 101", "General Inpatient"),
                ("Main Block", "1st Floor", "Ward A - Rm 102", "Treatment Room"),
                ("Main Block", "2nd Floor", "Oncology - Rm 204", "Chemotherapy & Oncology"),
                ("Main Block", "2nd Floor", "Pediatrics - Rm 212", "Pediatric Care"),
                ("Trauma Center", "Ground Floor", "Emergency Trauma 1", "Emergency Resuscitation"),
                ("Trauma Center", "Ground Floor", "Emergency Trauma 2", "Triage Bay"),
                ("Specialty Wing", "3rd Floor", "ICU Bed 04", "Intensive Care Unit"),
                ("Diagnostic Block", "Basement 1", "Pathology Lab Rm 3", "Specimen Testing"),
            ]
            for bldg, flr, r_no, w_type in default_rooms:
                conn.execute(
                    "INSERT INTO rooms(building, floor, room_number, ward_type) VALUES (?, ?, ?, ?)",
                    (bldg, flr, r_no, w_type)
                )

        # 3. Seed Robots
        robot_count = conn.execute("SELECT COUNT(*) AS c FROM robots").fetchone()["c"]
        if robot_count == 0:
            conn.execute(
                """INSERT INTO robots (id, robot_code, name, status, battery_percent, current_location, current_task, is_charging, e_stop_active, updated_at)
                   VALUES (1, 'BIONEX-AMR-01', 'BioNex Unit 01 (Autonomous)', 'Active / Ready', 92, 'Ward A Station', 'Awaiting Task', 0, 0, ?)""",
                (now,)
            )
            conn.execute(
                """INSERT INTO robots (id, robot_code, name, status, battery_percent, current_location, current_task, is_charging, e_stop_active, updated_at)
                   VALUES (2, 'BIONEX-AMR-02', 'BioNex Unit 02 (Standby)', 'Docked / Charging', 98, 'Central Docking Bay', 'Charging on Base', 1, 0, ?)""",
                (now,)
            )

        # 4. Seed Bins
        bin_count = conn.execute("SELECT COUNT(*) AS c FROM bin_status").fetchone()["c"]
        if bin_count == 0:
            bins_data = [
                (1, "Yellow", 35, 100, 1400.0),
                (1, "Red", 50, 100, 2100.0),
                (1, "White", 20, 100, 650.0),
                (1, "Blue", 15, 100, 800.0),
                (2, "Yellow", 10, 100, 400.0),
                (2, "Red", 25, 100, 950.0),
                (2, "White", 5, 100, 150.0),
                (2, "Blue", 10, 100, 300.0),
            ]
            for r_id, cat, fill, cap, wt in bins_data:
                conn.execute(
                    """INSERT OR IGNORE INTO bin_status (robot_id, category, fill_percent, capacity_percent, current_weight_grams, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (r_id, cat, fill, cap, wt, now)
                )

        # 5. Seed Collection Requests
        req_count = conn.execute("SELECT COUNT(*) AS c FROM collection_requests").fetchone()["c"]
        if req_count == 0:
            sample_requests = [
                ("Ward A - Rm 102", "Main Block", "1st Floor", "Nurse Sarah Jenkins", "Used disposable IV tubing & drip set", "Red", "Normal", "Completed", 1),
                ("ICU Bed 04", "Specialty Wing", "3rd Floor", "Nurse Priya Patel", "Used 24G syringe with needle", "White", "High", "In Progress", 1),
                ("Emergency Trauma 1", "Trauma Center", "Ground Floor", "Dr. Vikram Sharma", "Soiled blood gauze swabs from trauma case", "Yellow", "Emergency", "Completed", 1),
                ("Pathology Lab Rm 3", "Diagnostic Block", "Basement 1", "Technician Maya Sen", "Broken antibiotic glass ampoules", "Blue", "Normal", "Assigned", 1),
                ("Oncology - Rm 204", "Main Block", "2nd Floor", "Nurse Sarah Jenkins", "Unlabeled medicine bottle with yellowish residue", "Yellow", "High", "Human Review", 1),
                ("Pediatrics - Rm 212", "Main Block", "2nd Floor", "Nurse Sarah Jenkins", "Contaminated nitrile exam gloves", "Red", "Normal", "Pending", 1),
            ]
            for room, bldg, flr, req_by, desc, cat, prio, stat, r_id in sample_requests:
                conn.execute(
                    """INSERT INTO collection_requests
                       (room, building, floor, requested_by, item_description, category, priority, status, assigned_robot_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (room, bldg, flr, req_by, desc, cat, prio, stat, r_id, now, now)
                )

        # 6. Seed Waste Records
        rec_count = conn.execute("SELECT COUNT(*) AS c FROM waste_records").fetchone()["c"]
        if rec_count == 0:
            records = [
                (1, 1, "Ward A - Rm 102", "Red", "Used disposable IV tubing & drip set", 220.5, 1, now),
                (3, 1, "Emergency Trauma 1", "Yellow", "Soiled blood gauze swabs from trauma case", 450.0, 1, now),
            ]
            for req_id, r_id, room, cat, desc, wt, ver, c_time in records:
                conn.execute(
                    """INSERT INTO waste_records (request_id, robot_id, room, category, item_description, measured_weight_grams, deposit_verified, collected_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (req_id, r_id, room, cat, desc, wt, ver, c_time)
                )

        # 7. Seed Alerts
        alert_count = conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
        if alert_count == 0:
            sample_alerts = [
                (1, "system", "info", "BioNex Unit 01 initialized and connected to Hospital Wi-Fi & MQTT broker.", 0, None, now),
                (1, "bins", "warning", "Unit 01: Red waste bin reached 50% capacity. Plan next CBWTF transfer.", 0, None, now),
                (1, "classification", "warning", "Item flagged for Human Review in Oncology - Rm 204: chemical verification required.", 0, None, now),
            ]
            for r_id, a_type, sev, msg, res, r_by, c_time in sample_alerts:
                conn.execute(
                    """INSERT INTO alerts (robot_id, type, severity, message, is_resolved, resolved_by, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (r_id, a_type, sev, msg, res, r_by, c_time)
                )

        # 8. Seed Delivery Records (CBWTF Handover)
        del_count = conn.execute("SELECT COUNT(*) AS c FROM delivery_records").fetchone()["c"]
        if del_count == 0:
            conn.execute(
                """INSERT INTO delivery_records (manifest_code, facility_name, vehicle_number, total_weight_kg, category_breakdown, handover_time, staff_signature, acknowledgement_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "CBWTF-MANIFEST-2026-0891",
                    "Apex Enviro Care Authorized CBWTF Facility",
                    "AP-39-TZ-4412",
                    14.85,
                    '{"Yellow": 6.2, "Red": 5.4, "White": 1.75, "Blue": 1.5}',
                    now,
                    "Dr. Ramesh Gupta (Chief Infection Control)",
                    "SHA256:7b91d4e0821cba3e5f29910a34b22c81",
                )
            )

        # 9. Seed Uploaded Documents (RAG Knowledge Base)
        doc_count = conn.execute("SELECT COUNT(*) AS c FROM uploaded_documents").fetchone()["c"]
        if doc_count == 0:
            docs = [
                ("Bio-Medical Waste Management Rules 2016 (CPCB Schedule I & II)", "CPCB_Biomedical_Waste_Rules_2016.pdf", "PDF", 24, 480.5, "Dr. Ramesh Gupta", now),
                ("Hospital Infection Control Committee (HICC) Waste Segregation SOP", "Hospital_SOP_BMW_Collection_2026.pdf", "PDF", 16, 320.0, "Dr. Ramesh Gupta", now),
                ("BioNex AMR Autonomous Operation & Human Safety Protocols", "BioNex_AMR_Safety_Manual.pdf", "PDF", 12, 215.0, "Admin", now),
            ]
            for title, fname, ftype, chunks, size, upby, ctime in docs:
                conn.execute(
                    """INSERT INTO uploaded_documents (title, filename, file_type, chunk_count, file_size_kb, uploaded_by, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (title, fname, ftype, chunks, size, upby, ctime)
                )

        # 10. Seed Audit Logs
        audit_count = conn.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]
        if audit_count == 0:
            logs = [
                ("admin@bionex.hospital", "Admin", "SYSTEM_INIT", "Database schema validated and seeded", "127.0.0.1", now),
                ("admin@bionex.hospital", "Admin", "LOGIN", "Chief Infection Control Officer logged in", "192.168.1.10", now),
                ("nurse.sarah@bionex.hospital", "User", "CREATE_REQUEST", "Submitted waste collection request for Rm 102", "192.168.1.42", now),
            ]
            for u_email, role, action, res, ip, ts in logs:
                conn.execute(
                    """INSERT INTO audit_logs (user_email, role, action, resource, ip_address, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (u_email, role, action, res, ip, ts)
                )
