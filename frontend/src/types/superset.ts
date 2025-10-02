// Superset configuration and status types
export interface SupersetInfo {
    superset_url: string;
    is_configured: boolean;
    connection_status: 'connected' | 'authentication_failed' | 'connection_failed' | 'unknown';
    database_count?: number;
    dataset_count?: number;
    error?: string;
}

export type Connection = {
    analytics_ready: boolean;
    created_at: string; // ISO timestamp
    database_type: string;
    id: number;
    is_active: boolean;
    last_sync: string | null; // ISO timestamp or null
    last_tested: string; // ISO timestamp
    name: string;
    connection_status: 'connected' | 'disconnected' | 'authentication_failed' | 'connection_failed' | 'unknown';
    sync_frequency: 'daily' | 'weekly' | string; // extend as needed
};

export type ConnectionsResponse = {
    connections: Connection[];
    connections_count: number;
    error: string | null;
    status: 'connected' | 'authentication_failed' | 'connection_failed' | 'disconnected' | 'unknown';
};


export interface SupersetDatabase {
    id: number;
    database_name: string;
    sqlalchemy_uri?: string;
    expose_in_sqllab: boolean;
    allow_run_async: boolean;
    created_at?: string;
}

export interface SupersetDataset {
    id: number;
    table_name: string;
    database?: {
        id: number;
        database_name: string;
    };
    schema?: string;
    created_at?: string;
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

export interface SyncToSupersetRequest {
    connection_id: number;
}

export interface SyncToSupersetResponse {
    message: string;
    superset_database_id?: number;
    connection: any; // Or use your DatabaseConnection type
}

export interface CreateDatasetRequest {
    database_id: number;
    schema: string;
    table_name: string;
}

export interface CreateDatasetResponse {
    message: string;
    dataset: SupersetDataset;
}