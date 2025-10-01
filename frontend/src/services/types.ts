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