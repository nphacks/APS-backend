-- Create screenplays table in TiDB
CREATE TABLE IF NOT EXISTS screenplays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mongodb_id VARCHAR(64) NOT NULL UNIQUE,
    project_id VARCHAR(36) NOT NULL,
    parent_id INT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    title VARCHAR(255) NOT NULL,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    current_revision INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES screenplays(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_parent_id (parent_id),
    INDEX idx_mongodb_id (mongodb_id)
);
