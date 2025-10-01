/* eslint-disable @typescript-eslint/no-explicit-any */

import type { CreateConnectionRequest, CreateDocumentTableRequest, DatabaseConnection, DocumentResult, DocumentTable, ETLJob, ExtractDocumentResponse, ReExtractRequest, ReExtractResponse, User } from "../types";
import type { ConnectionsResponse, CreateDatasetRequest, CreateDatasetResponse, SupersetInfo, SyncAllConnectionsResponse, SyncToSupersetResponse } from "../types/superset";

const API_BASE_URL = import.meta.env.VITE_APP_API_URL || 'http://localhost:8000';

// Wrapper around fetch
async function apiFetch<T>(
    endpoint: string,
    options: RequestInit = {},
    isForm: boolean = false
): Promise<T> {
    const token = localStorage.getItem('access_token');

    const headers: HeadersInit = {
        ...(isForm ? { 'Content-Type': 'application/x-www-form-urlencoded' } : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Error ${response.status}`);
    }

    return response.json();
}

// ---------------- Services ---------------- //
export const authService = {
    login: (username: string, password: string) =>
        apiFetch<{ access_token: string }>(
            '/api/auth/login',
            {
                method: 'POST',
                body: JSON.stringify({ username, password })
            },
            false
        ),

    register: (userData: { email: string; username: string; password: string; full_name?: string }) =>
        apiFetch('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData),
        }),

    logout: () => {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    },

    forgotPassword: (email: string) =>
        apiFetch('/api/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email }),
        }),

    resetPassword: (token: string, newPassword: string) =>
        apiFetch('/api/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify({ token, new_password: newPassword }),
        }),

    getCurrentUser: () => apiFetch<User>('/api/auth/me'),
};

export const connectionService = {
    getConnections: () => apiFetch<DatabaseConnection[]>('/api/connections/'),

    createConnection: (connectionData: CreateConnectionRequest) =>
        apiFetch<DatabaseConnection>('/api/connections/', {
            method: 'POST',
            body: JSON.stringify(connectionData),
        }),

    getConnection: (id: number) => apiFetch<DatabaseConnection>(`/api/connections/${id}`),

    updateConnection: (id: number, updateData: Partial<DatabaseConnection>) =>
        apiFetch(`/api/connections/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updateData),
        }),

    deleteConnection: (id: number) =>
        apiFetch(`/api/connections/${id}`, { method: 'DELETE' }),

    testConnection: (id: number) =>
        apiFetch(`/api/connections/${id}/test`, { method: 'POST' }),
};

export const jobService = {
    getJobs: (connectionId?: number) =>
        apiFetch<ETLJob[]>(
            `/api/etl/jobs${connectionId ? `?connection_id=${connectionId}` : ''}`
        ),

    createJob: (jobData: { connection_id: number; job_type?: string }) =>
        apiFetch('/api/etl/jobs/', {
            method: 'POST',
            body: JSON.stringify(jobData),
        }),

    getJob: (id: number) => apiFetch<ETLJob>(`/api/etl/jobs/${id}`),

    triggerETLJob: (jobData: { connection_id: number; job_type?: string; trigger_type?: string }) =>
        apiFetch('/api/etl/jobs/trigger', {
            method: 'POST',
            body: JSON.stringify(jobData),
        }),

    triggerAllJobs: () =>
        apiFetch('/api/etl/jobs/trigger-all', { method: 'POST' }),

    getSchedule: (connectionId: number) =>
        apiFetch(`/api/etl/jobs/connection/${connectionId}/schedule`),
};


export const supersetService = {
    // Get Superset configuration and status
    getInfo: () => apiFetch<SupersetInfo>('/api/superset/info'),

    // Check connection status
    getStatus: () => apiFetch<ConnectionsResponse>('/api/superset/status'),

    // Sync connection to Superset
    syncConnection: (connectionId: number) =>
        apiFetch<SyncToSupersetResponse>(`/api/superset/sync/${connectionId}`, {
            method: 'POST'
        }),

    syncAllConnections: () =>
        apiFetch<SyncAllConnectionsResponse>('/api/superset/sync-all', {
            method: 'POST'
        }),

    // List Superset databases
    getDatabases: () =>
        apiFetch<{ databases: any[] }>('/api/superset/databases'),

    // List Superset datasets
    getDatasets: () =>
        apiFetch<{ datasets: any[] }>('/api/superset/datasets'),

    // Create dataset in Superset
    createDataset: (data: CreateDatasetRequest) =>
        apiFetch<CreateDatasetResponse>('/api/superset/datasets/create', {
            method: 'POST',
            body: JSON.stringify(data)
        })
};

export const settingsService = {
    getProfile: () => apiFetch<any>('/api/settings/profile'),
    updateProfile: (data: any) =>
        apiFetch('/api/settings/profile', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getUserSettings: () => apiFetch<any>('/api/settings/user-settings'),
    updateUserSettings: (data: any) =>
        apiFetch('/api/settings/user-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getConnectionSettings: () => apiFetch<any>('/api/settings/connection-settings'),
    updateConnectionSettings: (data: any) =>
        apiFetch('/api/settings/connection-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getETLSchedules: () => apiFetch<any>('/api/settings/etl-schedules'),
    updateETLSchedule: (connectionId: number, data: any) =>
        apiFetch(`/api/settings/etl-schedules/${connectionId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getAnalyticsSettings: () => apiFetch<any>('/api/settings/analytics-settings'),
    updateAnalyticsSettings: (data: any) =>
        apiFetch('/api/settings/analytics-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getNotificationSettings: () => apiFetch<any>('/api/settings/notification-settings'),
    updateNotificationSettings: (data: any) =>
        apiFetch('/api/settings/notification-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getSystemInfo: () => apiFetch<any>('/api/settings/system-info'),
};


// Add Document Extraction Service
export const documentService = {
    // List all document tables
    getTables: () =>
        apiFetch<DocumentTable[]>('/api/documents/tables'),

    // Get specific table configuration
    getTable: (tableId: string) =>
        apiFetch<DocumentTable>(`/api/documents/tables/${tableId}`),

    // Create or update document table
    createTable: (tableData: CreateDocumentTableRequest) =>
        apiFetch<DocumentTable>('/api/documents/tables', {
            method: 'POST',
            body: JSON.stringify(tableData),
        }),

    // Delete document table
    deleteTable: (tableId: string) =>
        apiFetch<{ message: string }>(`/api/documents/tables/${tableId}`, {
            method: 'DELETE',
        }),

    // Extract data from document
    extractDocument: async (file: File, table: any, model?: string) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('table', JSON.stringify(table));
        if (model) {
            formData.append('model', model);
        }

        const token = localStorage.getItem('access_token');
        const response = await fetch(`${API_BASE_URL}/api/documents/extract`, {
            method: 'POST',
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: formData,
        });

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `Error ${response.status}`);
        }

        return response.json() as Promise<ExtractDocumentResponse>;
    },

    // List extraction results
    getResults: (params?: { limit?: number; table_id?: string }) => {
        const queryParams = new URLSearchParams();
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        if (params?.table_id) queryParams.append('table_id', params.table_id);

        const queryString = queryParams.toString();
        return apiFetch<DocumentResult[]>(
            `/api/documents/results${queryString ? `?${queryString}` : ''}`
        );
    },

    // Get specific result
    getResult: (id: number) =>
        apiFetch<DocumentResult>(`/api/documents/results/${id}`),

    // Delete result
    deleteResult: (id: number) =>
        apiFetch<{ message: string }>(`/api/documents/results/${id}`, {
            method: 'DELETE',
        }),

    // Re-extract document with updated fields
    reExtract: (id: number, fields: ReExtractRequest) =>
        apiFetch<ReExtractResponse>(`/api/documents/results/${id}/re-extract`, {
            method: 'POST',
            body: JSON.stringify(fields),
        }),
};