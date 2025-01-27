 CREATE DATABASE IF NOT EXISTS email_warmup;
USE email_warmup;

CREATE TABLE credentials (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    provider ENUM('gmail', 'outlook') NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_tenant (user_id, tenant_id),
    UNIQUE KEY unique_email (email)
);

CREATE TABLE email_quotas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    daily_quota INT NOT NULL DEFAULT 5,
    used_quota INT NOT NULL DEFAULT 0,
    warmup_start_date DATE NOT NULL,
    last_reset_date DATE NOT NULL,
    FOREIGN KEY (email) REFERENCES credentials(email)
);

CREATE TABLE email_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL,
    from_email VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    status ENUM('queued', 'processing', 'sent', 'failed', 'delayed') NOT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_id (event_id),
    INDEX idx_status (status)
);