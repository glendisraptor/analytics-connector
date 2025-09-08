-- ============================================================================
-- analytics_connector_setup.sql
-- Complete PostgreSQL setup for Analytics Connector
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
        sync_frequency VARCHAR(50) DEFAULT 'daily',
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
    connection_id INTEGER NOT NULL,
    source_table_name VARCHAR(255) NOT NULL,
    analytics_table_name VARCHAR(255) NOT NULL,
    last_synced TIMESTAMP
    WITH
        TIME ZONE,
        record_count INTEGER DEFAULT 0,
        schema_info JSONB,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_metadata_connection ON data_source_metadata (connection_id);

CREATE INDEX IF NOT EXISTS idx_metadata_source ON data_source_metadata (source_table_name);

CREATE INDEX IF NOT EXISTS idx_metadata_analytics ON data_source_metadata (analytics_table_name);

-- -- ============================================================================
-- -- Ensure 'postgres' user exists and has full privileges
-- -- ============================================================================
-- DO
-- $$
-- BEGIN
--     -- Create user 'postgres' if it doesn't exist
--     IF NOT EXISTS (
--         SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres'
--     ) THEN
--         CREATE ROLE postgres LOGIN SUPERUSER PASSWORD 'admin';
--     END IF;
-- END
-- $$;

-- -- Grant all privileges on existing databases
-- GRANT ALL PRIVILEGES ON DATABASE analytics_connector TO postgres;
-- GRANT ALL PRIVILEGES ON DATABASE analytics_data TO postgres;

-- -- Grant privileges on all existing tables and sequences in both databases
-- \c analytics_connector
-- DO $$
-- BEGIN
--     EXECUTE 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;';
--     EXECUTE 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;';
-- END $$;

-- \c analytics_data
-- DO $$
-- BEGIN
--     EXECUTE 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;';
--     EXECUTE 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;';
-- END $$;

-- ============================================================================
-- TEST DATABASE
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

-- 11. Example query to join data
SELECT
    fr.id,
    fr.transaction_date,
    fr.description,
    fr.amount,
    fr.transaction_type,
    fr.category,
    u.first_name || ' ' || u.last_name AS user_name,
    d.name AS department_name
FROM
    financial_records fr
    JOIN users u ON fr.user_id = u.id
    JOIN departments d ON fr.department_id = d.id
ORDER BY fr.transaction_date;