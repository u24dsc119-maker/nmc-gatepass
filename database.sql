CREATE DATABASE IF NOT EXISTS nmcc_gatepass;
USE nmcc_gatepass;

DROP TABLE IF EXISTS visitors;

CREATE TABLE visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(100),
    purpose VARCHAR(255) NOT NULL,
    person_to_meet VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    token VARCHAR(255),
    entry_time DATETIME NULL,
    exit_time DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
