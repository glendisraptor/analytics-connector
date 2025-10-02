// User types
export interface User {
    id: number;
    email: string;
    username: string;
    full_name?: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
}

export interface AuthResponse {
    user: User;
    settings: UserSettings;
}

export interface UserSettings {
    theme: 'light' | 'dark' | 'system';
    notifications_enabled: boolean;
}

// Database Connection types
export interface DatabaseConnection {
    id: number;
    name: string;
    database_type: string;
    status: string;
    last_tested?: string;
    analytics_ready: boolean;
    last_sync?: string;
    is_active: boolean;
    sync_frequency: string;
    created_at: string;
}

export interface CreateConnectionRequest {
    name: string;
    database_type: string;
    credentials: ConnectionCredentials;
    sync_frequency?: string;
}

// ETL Job types
export interface ETLJob {
    id: number;
    connection_id: number;
    status: string;
    job_type: string;
    records_processed: number;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
    created_at: string;
}

// Superset types
export interface SupersetInfo {
    superset_url: string;
    is_configured: boolean;
    connection_status: 'connected' | 'authentication_failed' | 'connection_failed' | 'unknown';
    database_count?: number;
    dataset_count?: number;
    error?: string;
}

export interface ConnectionsResponse {
    status: string;
    superset_url: string;
    database_count: number;
}

export interface SyncToSupersetResponse {
    message: string;
    superset_database_id?: number;
    connection: DatabaseConnection;
}

export interface SyncResult {
    connection_id: number;
    connection_name: string;
    status: 'success' | 'failed' | 'skipped';
    superset_database_id?: number;
    message: string;
}

export interface SyncAllConnectionsResponse {
    message: string;
    total_connections: number;
    synced: number;
    failed: number;
    results: SyncResult[];
}

export interface CreateDatasetRequest {
    database_id: number;
    schema: string;
    table_name: string;
}

export interface CreateDatasetResponse {
    message: string;
    dataset: any;
}

// ------
/* eslint-disable @typescript-eslint/no-explicit-any */
// ---------------- Types ---------------- //
export interface User {
    id: number;
    email: string;
    username: string;
    full_name?: string;
    is_active: boolean;
}

export interface DatabaseConnection {
    id: number;
    name: string;
    database_type: string;
    status: string;
    last_tested?: string;
    last_sync?: string;
    analytics_ready: boolean;
    sync_frequency: string;
    is_active: boolean;
    created_at: string;
}

export interface ETLJob {
    id: number;
    connection_id: number;
    status: string;
    job_type: string;
    records_processed: number;
    error_message?: string;
    started_at?: string;
    completed_at?: string;
    created_at: string;
}

export interface ConnectionCredentials {
    host: string;
    port: number;
    username: string;
    password: string;
    database_name: string;
    additional_params?: Record<string, any>;
}

export interface CreateConnectionRequest {
    name: string;
    database_type: string;
    credentials: ConnectionCredentials;
    sync_frequency?: string;
}

export interface CreateJobRequest {
    connection_id: number;
    job_type?: string;
}

export interface ScheduleInfo {
    sync_frequency: string;
    next_scheduled_sync: string;
}

export interface ETLJobManagerProps {
    connectionId: number;
    connectionName: string;
    connectionStatus: string;
}

export interface ConnectionAnalyticsCardProps {
    connection: DatabaseConnection & { connection_id: number };
    connection_id: number;
    onSync: (connectionId: number) => void;
    isSyncing: boolean;
    supersetUrl?: string;
}

// Export document types
export * from './documents';
export * from './superset';