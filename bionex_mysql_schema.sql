CREATE DATABASE IF NOT EXISTS bionex_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bionex_db;

-- 1. Users & Roles
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    role ENUM('Admin', 'User') NOT NULL DEFAULT 'User',
    department VARCHAR(100) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_role (role)
) ENGINE=InnoDB;

-- 2. Hospital Rooms
CREATE TABLE IF NOT EXISTS rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    floor VARCHAR(50) NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    ward_type VARCHAR(100) NOT NULL,
    INDEX idx_room_number (room_number)
) ENGINE=InnoDB;

-- 3. Robots
CREATE TABLE IF NOT EXISTS robots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(60) NOT NULL DEFAULT 'Active / Ready',
    battery_percent INT NOT NULL DEFAULT 100,
    current_location VARCHAR(100) NOT NULL DEFAULT 'Dock Station',
    current_task VARCHAR(150) NOT NULL DEFAULT 'Standby',
    is_charging TINYINT(1) NOT NULL DEFAULT 0,
    e_stop_active TINYINT(1) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. Collection Requests
CREATE TABLE IF NOT EXISTS collection_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room VARCHAR(80) NOT NULL,
    building VARCHAR(100) NOT NULL DEFAULT 'Main Block',
    floor VARCHAR(50) NOT NULL DEFAULT '1st Floor',
    requested_by VARCHAR(100) NOT NULL,
    item_description VARCHAR(300) NOT NULL,
    category ENUM('Yellow', 'Red', 'White', 'Blue', 'Human Review') NOT NULL,
    priority ENUM('Normal', 'High', 'Emergency') NOT NULL DEFAULT 'Normal',
    status ENUM('Pending', 'Assigned', 'In Progress', 'Completed', 'Human Review', 'Cancelled') NOT NULL DEFAULT 'Pending',
    assigned_robot_id INT DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_robot_id) REFERENCES robots(id) ON DELETE SET NULL,
    INDEX idx_req_status (status),
    INDEX idx_req_priority (priority)
) ENGINE=InnoDB;

-- 5. Waste Records
CREATE TABLE IF NOT EXISTS waste_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NULL,
    robot_id INT NOT NULL DEFAULT 1,
    room VARCHAR(80) NOT NULL,
    category ENUM('Yellow', 'Red', 'White', 'Blue') NOT NULL,
    item_description VARCHAR(300) NOT NULL,
    measured_weight_grams DECIMAL(8, 2) NOT NULL DEFAULT 150.00,
    deposit_verified TINYINT(1) NOT NULL DEFAULT 1,
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES collection_requests(id) ON DELETE SET NULL,
    FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE,
    INDEX idx_waste_category (category)
) ENGINE=InnoDB;

-- 6. Bin Status
CREATE TABLE IF NOT EXISTS bin_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id INT NOT NULL DEFAULT 1,
    category ENUM('Yellow', 'Red', 'White', 'Blue') NOT NULL,
    fill_percent INT NOT NULL DEFAULT 0,
    capacity_percent INT NOT NULL DEFAULT 100,
    current_weight_grams DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_robot_category (robot_id, category),
    FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 7. Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id INT DEFAULT 1,
    type VARCHAR(50) NOT NULL DEFAULT 'system',
    severity ENUM('info', 'warning', 'danger') NOT NULL DEFAULT 'info',
    message VARCHAR(255) NOT NULL,
    is_resolved TINYINT(1) NOT NULL DEFAULT 0,
    resolved_by VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL
) ENGINE=InnoDB;

-- 8. Robot Logs
CREATE TABLE IF NOT EXISTS robot_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id INT NOT NULL DEFAULT 1,
    event_type VARCHAR(80) NOT NULL,
    details TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 9. Delivery Records
CREATE TABLE IF NOT EXISTS delivery_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manifest_code VARCHAR(100) NOT NULL UNIQUE,
    facility_name VARCHAR(150) NOT NULL,
    vehicle_number VARCHAR(50) NOT NULL,
    total_weight_kg DECIMAL(8, 2) NOT NULL,
    category_breakdown JSON NOT NULL,
    handover_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    staff_signature VARCHAR(150) NOT NULL,
    acknowledgement_hash VARCHAR(128) NOT NULL
) ENGINE=InnoDB;

-- 10. Uploaded Documents
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    filename VARCHAR(200) NOT NULL,
    file_type VARCHAR(20) NOT NULL DEFAULT 'PDF',
    chunk_count INT NOT NULL DEFAULT 0,
    file_size_kb DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    uploaded_by VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 11. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(120) NOT NULL,
    role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(200) NOT NULL,
    ip_address VARCHAR(45) NOT NULL DEFAULT '127.0.0.1',
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_timestamp (timestamp)
) ENGINE=InnoDB;
