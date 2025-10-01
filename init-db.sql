-- ============================================================================
-- analytics_connector_setup.sql
-- Complete PostgreSQL setup for Analytics Connector with Settings
-- ============================================================================

-- Create databases (only if they don't exist)
SELECT 'CREATE DATABASE analytics_connector'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytics_connector')\gexec

SELECT 'CREATE DATABASE analytics_data'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytics_data')\gexec

-- ============================================================================
-- Connect to analytics_connector database to create application tables
-- ============================================================================
\c analytics_connector;

-- Create ENUM types for better data integrity (only if they don't exist)
DO $$ BEGIN
    CREATE TYPE database_type_enum AS ENUM (
        'postgresql', 'mysql', 'mongodb', 'sqlite', 'oracle', 'mssql'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE connection_status_enum AS ENUM (
        'pending', 'connected', 'failed', 'testing'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status_enum AS ENUM (
        'pending', 'running', 'completed', 'failed'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sync_frequency_enum AS ENUM (
        'hourly', 'daily', 'weekly', 'monthly'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE theme_enum AS ENUM (
        'light', 'dark', 'system'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- USERS TABLE - Authentication and user management
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active);

-- Create update trigger function (replace if exists for updates)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger (drop and recreate to avoid conflicts)
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- USER_SETTINGS TABLE - User preferences and configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,

-- Connection Settings
auto_sync_to_superset BOOLEAN DEFAULT TRUE,
default_sync_frequency sync_frequency_enum DEFAULT 'daily',
connection_timeout INTEGER DEFAULT 30,
max_retry_attempts INTEGER DEFAULT 3,

-- Analytics Settings
superset_auto_create_datasets BOOLEAN DEFAULT TRUE,
superset_auto_create_dashboards BOOLEAN DEFAULT FALSE,
data_retention_days INTEGER DEFAULT 365,
enable_data_profiling BOOLEAN DEFAULT TRUE,

-- Notification Settings
email_notifications BOOLEAN DEFAULT TRUE,
etl_success_notifications BOOLEAN DEFAULT FALSE,
etl_failure_notifications BOOLEAN DEFAULT TRUE,
weekly_reports BOOLEAN DEFAULT FALSE,

-- UI Settings
theme theme_enum DEFAULT 'light',
timezone VARCHAR(50) DEFAULT 'UTC',
date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD',

-- Additional settings as JSON


additional_settings JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id)
);

-- Create indexes for user_settings
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings (user_id);

-- Create trigger for user_settings
DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;

CREATE TRIGGER update_user_settings_updated_at 
    BEFORE UPDATE ON user_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATABASE_CONNECTIONS TABLE - Customer database connections
-- ============================================================================
CREATE TABLE IF NOT EXISTS database_connections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    database_type database_type_enum NOT NULL,
    encrypted_credentials TEXT NOT NULL,
    status connection_status_enum DEFAULT 'pending',
    last_tested TIMESTAMP
    WITH
        TIME ZONE,
        analytics_ready BOOLEAN DEFAULT FALSE,
        last_sync TIMESTAMP
    WITH
        TIME ZONE,
        is_active BOOLEAN DEFAULT TRUE,
        sync_frequency sync_frequency_enum DEFAULT 'daily',
        owner_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_connections_owner ON database_connections (owner_id);

CREATE INDEX IF NOT EXISTS idx_connections_type ON database_connections (database_type);

CREATE INDEX IF NOT EXISTS idx_connections_status ON database_connections (status);

CREATE INDEX IF NOT EXISTS idx_connections_active ON database_connections (is_active);

-- Create trigger (drop and recreate to avoid conflicts)
DROP TRIGGER IF EXISTS update_connections_updated_at ON database_connections;

CREATE TRIGGER update_connections_updated_at 
    BEFORE UPDATE ON database_connections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ETL_SCHEDULES TABLE - ETL job scheduling configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS etl_schedules (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES database_connections (id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,

-- Schedule Configuration
frequency sync_frequency_enum NOT NULL DEFAULT 'daily',
scheduled_time VARCHAR(8) DEFAULT '02:00', -- HH:MM format
timezone VARCHAR(50) DEFAULT 'UTC',
is_active BOOLEAN DEFAULT TRUE,

-- Advanced Options
days_of_week VARCHAR(20), -- For weekly: "1,3,5" (Mon, Wed, Fri)
day_of_month INTEGER, -- For monthly: 1-31

-- Last execution tracking


last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(connection_id)
);

-- Create indexes for etl_schedules
CREATE INDEX IF NOT EXISTS idx_etl_schedules_connection_id ON etl_schedules (connection_id);

CREATE INDEX IF NOT EXISTS idx_etl_schedules_user_id ON etl_schedules (user_id);

CREATE INDEX IF NOT EXISTS idx_etl_schedules_active ON etl_schedules (is_active);

CREATE INDEX IF NOT EXISTS idx_etl_schedules_next_run ON etl_schedules (next_run);

-- Create trigger for etl_schedules
DROP TRIGGER IF EXISTS update_etl_schedules_updated_at ON etl_schedules;

CREATE TRIGGER update_etl_schedules_updated_at 
    BEFORE UPDATE ON etl_schedules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ETL_JOBS TABLE - Background job tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS etl_jobs (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES database_connections (id) ON DELETE CASCADE,
    status job_status_enum DEFAULT 'pending',
    job_type VARCHAR(50) DEFAULT 'full_sync',
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP
    WITH
        TIME ZONE,
        completed_at TIMESTAMP
    WITH
        TIME ZONE,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_jobs_connection ON etl_jobs (connection_id);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON etl_jobs (status);

CREATE INDEX IF NOT EXISTS idx_jobs_created ON etl_jobs (created_at);

CREATE INDEX IF NOT EXISTS idx_jobs_type ON etl_jobs (job_type);

-- Create trigger (drop and recreate to avoid conflicts)
DROP TRIGGER IF EXISTS update_jobs_updated_at ON etl_jobs;

CREATE TRIGGER update_jobs_updated_at 
    BEFORE UPDATE ON etl_jobs 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- AUDIT_LOGS TABLE - Security and access logging
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs (user_id);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs (action);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at);

CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs (resource_type, resource_id);

-- ============================================================================
-- Insert initial data for testing (only if admin user doesn't exist)
-- ============================================================================
INSERT INTO
    users (
        email,
        username,
        hashed_password,
        full_name,
        is_superuser
    )
SELECT 'admin@analyticsconnector.com', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewgHXVyYNECJZVia', 'System Administrator', TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM users
        WHERE
            email = 'admin@analyticsconnector.com'
    );

-- Create default settings for admin user
INSERT INTO
    user_settings (user_id)
SELECT u.id
FROM users u
WHERE
    u.email = 'admin@analyticsconnector.com'
    AND NOT EXISTS (
        SELECT 1
        FROM user_settings us
        WHERE
            us.user_id = u.id
    );

-- ============================================================================
-- Create views for easier querying (replace if exists)
-- ============================================================================

-- View for connection statistics
CREATE OR REPLACE VIEW connection_stats AS
SELECT
    u.username,
    COUNT(dc.id) as total_connections,
    COUNT(
        CASE
            WHEN dc.status = 'connected' THEN 1
        END
    ) as active_connections,
    COUNT(
        CASE
            WHEN dc.status = 'failed' THEN 1
        END
    ) as failed_connections,
    MAX(dc.last_sync) as latest_sync
FROM
    users u
    LEFT JOIN database_connections dc ON u.id = dc.owner_id
WHERE
    u.is_active = TRUE
GROUP BY
    u.id,
    u.username;

-- View for job statistics
CREATE OR REPLACE VIEW job_stats AS
SELECT
    dc.name as connection_name,
    dc.database_type,
    COUNT(ej.id) as total_jobs,
    COUNT(
        CASE
            WHEN ej.status = 'completed' THEN 1
        END
    ) as completed_jobs,
    COUNT(
        CASE
            WHEN ej.status = 'failed' THEN 1
        END
    ) as failed_jobs,
    SUM(ej.records_processed) as total_records_processed,
    MAX(ej.completed_at) as last_successful_job
FROM
    database_connections dc
    LEFT JOIN etl_jobs ej ON dc.id = ej.connection_id
GROUP BY
    dc.id,
    dc.name,
    dc.database_type;

-- View for user settings with defaults
CREATE OR REPLACE VIEW user_settings_view AS
SELECT
    u.id as user_id,
    u.username,
    u.email,
    COALESCE(
        us.auto_sync_to_superset,
        TRUE
    ) as auto_sync_to_superset,
    COALESCE(
        us.default_sync_frequency,
        'daily'
    ) as default_sync_frequency,
    COALESCE(us.connection_timeout, 30) as connection_timeout,
    COALESCE(us.max_retry_attempts, 3) as max_retry_attempts,
    COALESCE(
        us.superset_auto_create_datasets,
        TRUE
    ) as superset_auto_create_datasets,
    COALESCE(
        us.superset_auto_create_dashboards,
        FALSE
    ) as superset_auto_create_dashboards,
    COALESCE(us.data_retention_days, 365) as data_retention_days,
    COALESCE(
        us.enable_data_profiling,
        TRUE
    ) as enable_data_profiling,
    COALESCE(us.email_notifications, TRUE) as email_notifications,
    COALESCE(
        us.etl_success_notifications,
        FALSE
    ) as etl_success_notifications,
    COALESCE(
        us.etl_failure_notifications,
        TRUE
    ) as etl_failure_notifications,
    COALESCE(us.weekly_reports, FALSE) as weekly_reports,
    COALESCE(us.theme, 'light') as theme,
    COALESCE(us.timezone, 'UTC') as timezone,
    COALESCE(us.date_format, 'YYYY-MM-DD') as date_format
FROM users u
    LEFT JOIN user_settings us ON u.id = us.user_id
WHERE
    u.is_active = TRUE;

-- View for ETL schedule overview
CREATE OR REPLACE VIEW etl_schedule_overview AS
SELECT
    es.id,
    dc.name as connection_name,
    dc.database_type,
    u.username as owner,
    es.frequency,
    es.scheduled_time,
    es.timezone,
    es.is_active,
    es.last_run,
    es.next_run,
    CASE
        WHEN es.next_run IS NOT NULL
        AND es.next_run <= CURRENT_TIMESTAMP THEN TRUE
        ELSE FALSE
    END as should_run_now
FROM
    etl_schedules es
    JOIN database_connections dc ON es.connection_id = dc.id
    JOIN users u ON es.user_id = u.id;

-- ============================================================================
-- Switch to analytics_data database for analytics tables
-- ============================================================================
\c analytics_data;

-- ============================================================================
-- ANALYTICS DATA SCHEMA
-- Tables here will be created dynamically by the ETL process
-- This is where customer data will be stored for analytics
-- ============================================================================

-- Metadata table to track which customer data tables exist
CREATE TABLE IF NOT EXISTS data_source_metadata (
    id SERIAL PRIMARY KEY,
    connection_id INT NOT NULL,
    source_table_name TEXT NOT NULL,
    analytics_table_name TEXT NOT NULL,
    last_synced TIMESTAMP
    WITH
        TIME ZONE,
        record_count INT DEFAULT 0,
        schema_info JSONB,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (
            connection_id,
            source_table_name
        )
);

-- Create indexes (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_metadata_connection ON data_source_metadata (connection_id);

CREATE INDEX IF NOT EXISTS idx_metadata_source ON data_source_metadata (source_table_name);

CREATE INDEX IF NOT EXISTS idx_metadata_analytics ON data_source_metadata (analytics_table_name);

-- ============================================================================
-- TEST DATABASE - Sample data for testing
-- Create a separate test database for running tests
-- ============================================================================

-- 1. Create the database
CREATE DATABASE company_finance;

-- Connect to the database
\c company_finance;

-- 2. Create a table for company departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    manager_id INT, -- references users later
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create a table for users/employees
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    department_id INT REFERENCES departments (id),
    role VARCHAR(50), -- e.g., 'Employee', 'Manager', 'Finance'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create a table for budgets (departmental budgets)
CREATE TABLE budgets (
    id SERIAL PRIMARY KEY,
    department_id INT REFERENCES departments (id),
    fiscal_year INT NOT NULL,
    allocated_amount NUMERIC(12, 2) NOT NULL,
    spent_amount NUMERIC(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Create a table for financial transactions
CREATE TABLE financial_records (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users (id),
    department_id INT REFERENCES departments (id),
    transaction_date DATE NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- 'Income' or 'Expense'
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Insert sample departments
INSERT INTO
    departments (name)
VALUES ('Finance'),
    ('Engineering'),
    ('Marketing');

-- 7. Insert sample users
INSERT INTO
    users (
        first_name,
        last_name,
        email,
        department_id,
        role
    )
VALUES (
        'Alice',
        'Johnson',
        'alice.johnson@example.com',
        1,
        'Finance Manager'
    ),
    (
        'Bob',
        'Smith',
        'bob.smith@example.com',
        2,
        'Engineer'
    ),
    (
        'Carol',
        'Taylor',
        'carol.taylor@example.com',
        2,
        'Engineering Manager'
    ),
    (
        'David',
        'Brown',
        'david.brown@example.com',
        3,
        'Marketing Specialist'
    ),
    (
        'Eva',
        'White',
        'eva.white@example.com',
        1,
        'Accountant'
    );

-- 8. Assign managers to departments
UPDATE departments SET manager_id = 1 WHERE name = 'Finance';

UPDATE departments SET manager_id = 3 WHERE name = 'Engineering';

UPDATE departments SET manager_id = 4 WHERE name = 'Marketing';

-- 9. Insert sample budgets
INSERT INTO
    budgets (
        department_id,
        fiscal_year,
        allocated_amount,
        spent_amount
    )
VALUES (1, 2025, 50000.00, 12000.00),
    (2, 2025, 80000.00, 35000.00),
    (3, 2025, 30000.00, 15000.00);

-- 10. Insert sample financial records
INSERT INTO
    financial_records (
        user_id,
        department_id,
        transaction_date,
        description,
        amount,
        transaction_type,
        category
    )
VALUES (
        1,
        1,
        '2025-01-05',
        'Client Payment - Project Alpha',
        15000.00,
        'Income',
        'Sales'
    ),
    (
        5,
        1,
        '2025-01-10',
        'Office Rent - January',
        2500.00,
        'Expense',
        'Rent'
    ),
    (
        2,
        2,
        '2025-01-12',
        'Salary - Bob Smith',
        4000.00,
        'Expense',
        'Salary'
    ),
    (
        4,
        3,
        '2025-01-15',
        'Social Media Campaign',
        1200.00,
        'Expense',
        'Marketing'
    ),
    (
        1,
        1,
        '2025-01-20',
        'Consulting Income',
        5000.00,
        'Income',
        'Consulting'
    ),
    (
        2,
        2,
        '2025-01-22',
        'New Laptop Purchase',
        1800.00,
        'Expense',
        'Equipment'
    ),
    (
        4,
        3,
        '2025-01-25',
        'Event Sponsorship',
        2500.00,
        'Expense',
        'Marketing'
    ),
    (
        5,
        1,
        '2025-01-28',
        'Software Subscription',
        200.00,
        'Expense',
        'Utilities'
    ),
    (
        3,
        2,
        '2025-01-30',
        'Cloud Hosting Fee',
        800.00,
        'Expense',
        'IT'
    ),
    (
        1,
        1,
        '2025-02-01',
        'Client Payment - Project Beta',
        12000.00,
        'Income',
        'Sales'
    );

-- ============================================================================
-- SUMMARY
-- ============================================================================
\c analytics_connector;

-- ============================================================================
-- DOCUMENT EXTRACTION TABLES
-- Add these to the analytics_connector database
-- ============================================================================

\c analytics_connector;

-- ============================================================================
-- DOCUMENT_TABLES - Configuration for document types and their fields
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_tables (
    id SERIAL PRIMARY KEY,
    table_id VARCHAR(100) UNIQUE NOT NULL, -- e.g., "financial", "invoices"
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_configured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    owner_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_document_tables_owner ON document_tables (owner_id);

CREATE INDEX IF NOT EXISTS idx_document_tables_table_id ON document_tables (table_id);

CREATE INDEX IF NOT EXISTS idx_document_tables_active ON document_tables (is_active);

-- ============================================================================
-- DOCUMENT_FIELDS - Field definitions for each document table
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_fields (
    id SERIAL PRIMARY KEY,
    field_id VARCHAR(100) NOT NULL, -- e.g., "amount", "iban"
    document_table_id INTEGER NOT NULL REFERENCES document_tables (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL, -- 'text', 'currency', 'date', 'number', 'email'
    is_required BOOLEAN DEFAULT FALSE,
    validation_rules JSONB, -- Store regex patterns, min/max values, etc.
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (document_table_id, field_id)
);

CREATE INDEX IF NOT EXISTS idx_document_fields_table ON document_fields (document_table_id);

CREATE INDEX IF NOT EXISTS idx_document_fields_field_id ON document_fields (field_id);

CREATE INDEX IF NOT EXISTS idx_document_fields_order ON document_fields (
    document_table_id,
    display_order
);

-- ============================================================================
-- DOCUMENT_RESULTS - Renamed from your existing table for consistency
-- This matches your existing DocumentResult model
-- ============================================================================
-- Note: Your app already has this table, but here's the enhanced version

DROP TABLE IF EXISTS document_results CASCADE;

CREATE TABLE document_results (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    stored_path VARCHAR(1024),
    file_hash VARCHAR(64),  -- For deduplication
    file_size INTEGER,

-- Link to document table configuration
document_table_id INTEGER REFERENCES document_tables (id) ON DELETE SET NULL,
table_id VARCHAR(255), -- Keep for backward compatibility
table_name VARCHAR(255),

-- Extraction results
fields_mapped JSONB, -- Mapped by field_id
fields_by_name JSONB, -- Mapped by field name
extracted_text TEXT, -- Full extracted text from document

-- Processing metadata
model_id VARCHAR(255),
extraction_method VARCHAR(50) DEFAULT 'groq', -- 'groq', 'regex', 'ocr'
processing_time_ms INTEGER,
confidence_score DECIMAL(3, 2), -- 0.00 to 1.00

-- Status and ownership
status VARCHAR(50) DEFAULT 'completed', -- 'pending', 'processing', 'completed', 'failed'
error_message TEXT,
owner_id INTEGER REFERENCES users (id) ON DELETE SET NULL,

-- Timestamps
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_results_filename ON document_results (filename);

CREATE INDEX IF NOT EXISTS idx_results_table ON document_results (document_table_id);

CREATE INDEX IF NOT EXISTS idx_results_owner ON document_results (owner_id);

CREATE INDEX IF NOT EXISTS idx_results_status ON document_results (status);

CREATE INDEX IF NOT EXISTS idx_results_created ON document_results (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_results_file_hash ON document_results (file_hash);

-- ============================================================================
-- Add triggers for updated_at
-- ============================================================================
DROP TRIGGER IF EXISTS update_document_tables_updated_at ON document_tables;

CREATE TRIGGER update_document_tables_updated_at 
    BEFORE UPDATE ON document_tables 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_document_fields_updated_at ON document_fields;

CREATE TRIGGER update_document_fields_updated_at 
    BEFORE UPDATE ON document_fields 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_document_results_updated_at ON document_results;

CREATE TRIGGER update_document_results_updated_at 
    BEFORE UPDATE ON document_results 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA - Initial document table configuration
-- ============================================================================

-- Insert the Financial Documents table
INSERT INTO
    document_tables (
        table_id,
        name,
        description,
        is_configured,
        owner_id
    )
SELECT 'financial', 'Financial Documents', 'Financial documents including invoices and receipts', TRUE, u.id
FROM users u
WHERE
    u.email = 'admin@analyticsconnector.com' ON CONFLICT (table_id) DO NOTHING;

-- Insert fields for Financial Documents
INSERT INTO
    document_fields (
        field_id,
        document_table_id,
        name,
        field_type,
        is_required,
        display_order
    )
SELECT 'amount', dt.id, 'Amount', 'currency', TRUE, 1
FROM document_tables dt
WHERE
    dt.table_id = 'financial' ON CONFLICT (document_table_id, field_id) DO NOTHING;

INSERT INTO
    document_fields (
        field_id,
        document_table_id,
        name,
        field_type,
        is_required,
        display_order
    )
SELECT 'iban', dt.id, 'IBAN', 'text', TRUE, 2
FROM document_tables dt
WHERE
    dt.table_id = 'financial' ON CONFLICT (document_table_id, field_id) DO NOTHING;

INSERT INTO
    document_fields (
        field_id,
        document_table_id,
        name,
        field_type,
        is_required,
        display_order
    )
SELECT 'country', dt.id, 'Country', 'text', TRUE, 3
FROM document_tables dt
WHERE
    dt.table_id = 'financial' ON CONFLICT (document_table_id, field_id) DO NOTHING;

INSERT INTO
    document_fields (
        field_id,
        document_table_id,
        name,
        field_type,
        is_required,
        display_order
    )
SELECT 'date', dt.id, 'Date', 'date', TRUE, 4
FROM document_tables dt
WHERE
    dt.table_id = 'financial' ON CONFLICT (document_table_id, field_id) DO NOTHING;

-- ============================================================================
-- SEED DATA - Sample extracted documents
-- ============================================================================

-- Insert sample document results with the admin user as owner
INSERT INTO
    document_results (
        filename,
        stored_path,
        document_table_id,
        table_id,
        table_name,
        fields_mapped,
        fields_by_name,
        extracted_text,
        model_id,
        owner_id,
        status,
        created_at
    )
SELECT
    'file1234.dcm',
    'uploads/file1234.dcm',
    dt.id,
    'financial',
    'Financial Documents',
    jsonb_build_object (
        'amount',
        '$650.00',
        'iban',
        'NL68RG8...',
        'country',
        'The Netherlands',
        'date',
        '2023-11-05'
    ),
    jsonb_build_object (
        'Amount',
        '$650.00',
        'IBAN',
        'NL68RG8...',
        'Country',
        'The Netherlands',
        'Date',
        '2023-11-05'
    ),
    'In a laoreet purus. Integer ipsum quam, lac...',
    'llama-3.1-8b-instant',
    u.id,
    'completed',
    '2023-11-05 10:30:00'
FROM document_tables dt, users u
WHERE
    dt.table_id = 'financial'
    AND u.email = 'admin@analyticsconnector.com'
LIMIT 1;

INSERT INTO
    document_results (
        filename,
        stored_path,
        document_table_id,
        table_id,
        table_name,
        fields_mapped,
        fields_by_name,
        extracted_text,
        model_id,
        owner_id,
        status,
        created_at
    )
SELECT
    'file1234_2.dcm',
    'uploads/file1234_2.dcm',
    dt.id,
    'financial',
    'Financial Documents',
    jsonb_build_object (
        'amount',
        '$600.50',
        'iban',
        'NL83RA5D...',
        'country',
        'The Netherlands',
        'date',
        '2023-11-07'
    ),
    jsonb_build_object (
        'Amount',
        '$600.50',
        'IBAN',
        'NL83RA5D...',
        'Country',
        'The Netherlands',
        'Date',
        '2023-11-07'
    ),
    'Aliquam pulvinar vestibulum blandit. Donec...',
    'llama-3.1-8b-instant',
    u.id,
    'completed',
    '2023-11-07 14:20:00'
FROM document_tables dt, users u
WHERE
    dt.table_id = 'financial'
    AND u.email = 'admin@analyticsconnector.com'
LIMIT 1;

INSERT INTO
    document_results (
        filename,
        stored_path,
        document_table_id,
        table_id,
        table_name,
        fields_mapped,
        fields_by_name,
        extracted_text,
        model_id,
        owner_id,
        status,
        created_at
    )
SELECT
    'file1234_3.dcm',
    'uploads/file1234_3.dcm',
    dt.id,
    'financial',
    'Financial Documents',
    jsonb_build_object (
        'amount',
        '$900.20',
        'iban',
        'LU0301023...',
        'country',
        'Luxembourg',
        'date',
        '2023-11-10'
    ),
    jsonb_build_object (
        'Amount',
        '$900.20',
        'IBAN',
        'LU0301023...',
        'Country',
        'Luxembourg',
        'Date',
        '2023-11-10'
    ),
    'Aliquam porta nisl ex, congue pellentes...',
    'llama-3.1-8b-instant',
    u.id,
    'completed',
    '2023-11-10 09:15:00'
FROM document_tables dt, users u
WHERE
    dt.table_id = 'financial'
    AND u.email = 'admin@analyticsconnector.com'
LIMIT 1;

-- Add remaining sample records...
INSERT INTO
    document_results (
        filename,
        stored_path,
        document_table_id,
        table_id,
        table_name,
        fields_mapped,
        fields_by_name,
        extracted_text,
        model_id,
        owner_id,
        status,
        created_at
    )
SELECT
    'file1234_4.dcm',
    'uploads/file1234_4.dcm',
    dt.id,
    'financial',
    'Financial Documents',
    jsonb_build_object (
        'amount',
        '$350.75',
        'iban',
        'LU1801012...',
        'country',
        'Luxembourg',
        'date',
        '2023-11-12'
    ),
    jsonb_build_object (
        'Amount',
        '$350.75',
        'IBAN',
        'LU1801012...',
        'Country',
        'Luxembourg',
        'Date',
        '2023-11-12'
    ),
    'In a laoreet purus. Integer ipsum quam, lac...',
    'llama-3.1-8b-instant',
    u.id,
    'completed',
    '2023-11-12 11:45:00'
FROM document_tables dt, users u
WHERE
    dt.table_id = 'financial'
    AND u.email = 'admin@analyticsconnector.com'
LIMIT 1;

-- Continue with remaining records (5-8)...

-- ============================================================================
-- VIEWS for easier querying
-- ============================================================================

CREATE OR REPLACE VIEW document_extraction_stats AS
SELECT
    dt.table_id,
    dt.name as table_name,
    COUNT(dr.id) as total_documents,
    COUNT(
        CASE
            WHEN dr.status = 'completed' THEN 1
        END
    ) as completed_count,
    COUNT(
        CASE
            WHEN dr.status = 'failed' THEN 1
        END
    ) as failed_count,
    AVG(dr.processing_time_ms) as avg_processing_time_ms,
    AVG(dr.confidence_score) as avg_confidence,
    MAX(dr.created_at) as last_extraction
FROM
    document_tables dt
    LEFT JOIN document_results dr ON dt.id = dr.document_table_id
GROUP BY
    dt.id,
    dt.table_id,
    dt.name;

CREATE OR REPLACE VIEW document_fields_view AS
SELECT
    dt.table_id,
    dt.name as table_name,
    df.field_id,
    df.name as field_name,
    df.field_type,
    df.is_required,
    df.display_order
FROM
    document_tables dt
    JOIN document_fields df ON dt.id = df.document_table_id
WHERE
    dt.is_active = TRUE
ORDER BY dt.table_id, df.display_order;

-- ============================================================================
SELECT 'Document extraction tables created successfully!' as status;

SELECT 'Database setup completed successfully!' as status;

SELECT 'Created tables:' as info;

SELECT table_name
FROM information_schema.tables
WHERE
    table_schema = 'public'
ORDER BY table_name;