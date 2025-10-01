/* eslint-disable @typescript-eslint/no-explicit-any */

import type { CreateConnectionRequest, DatabaseConnection, ETLJob, User } from "./types";

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
            '/api/v1/auth/login',
            {
                method: 'POST',
                body: new URLSearchParams({ username, password }),
            },
            true
        ),

    register: (userData: { email: string; username: string; password: string; full_name?: string }) =>
        apiFetch('/api/v1/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData),
        }),

    getCurrentUser: () => apiFetch<User>('/api/v1/auth/me'),
};

export const connectionService = {
    getConnections: () => apiFetch<DatabaseConnection[]>('/api/v1/connections/'),

    createConnection: (connectionData: CreateConnectionRequest) =>
        apiFetch<DatabaseConnection>('/api/v1/connections/', {
            method: 'POST',
            body: JSON.stringify(connectionData),
        }),

    getConnection: (id: number) => apiFetch<DatabaseConnection>(`/api/v1/connections/${id}`),

    updateConnection: (id: number, updateData: Partial<DatabaseConnection>) =>
        apiFetch(`/api/v1/connections/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updateData),
        }),

    deleteConnection: (id: number) =>
        apiFetch(`/api/v1/connections/${id}`, { method: 'DELETE' }),

    testConnection: (id: number) =>
        apiFetch(`/api/v1/connections/${id}/test`, { method: 'POST' }),
};

export const jobService = {
    getJobs: (connectionId?: number) =>
        apiFetch<ETLJob[]>(
            `/api/v1/jobs/${connectionId ? `?connection_id=${connectionId}` : ''}`
        ),

    createJob: (jobData: { connection_id: number; job_type?: string }) =>
        apiFetch('/api/v1/jobs/', {
            method: 'POST',
            body: JSON.stringify(jobData),
        }),

    getJob: (id: number) => apiFetch<ETLJob>(`/api/v1/jobs/${id}`),

    triggerETLJob: (jobData: { connection_id: number; job_type?: string; trigger_type?: string }) =>
        apiFetch('/api/v1/jobs/trigger', {
            method: 'POST',
            body: JSON.stringify(jobData),
        }),

    triggerAllJobs: () =>
        apiFetch('/api/v1/jobs/trigger-all', { method: 'POST' }),

    getSchedule: (connectionId: number) =>
        apiFetch(`/api/v1/jobs/connection/${connectionId}/schedule`),
};

export const analyticsService = {
    getSupersetInfo: () => apiFetch<any>('/api/v1/analytics/superset-info'),

    getConnectionsStatus: () => apiFetch<any>('/api/v1/analytics/connections-status'),

    syncConnectionToSuperset: (connectionId: number) =>
        apiFetch(`/api/v1/connections/${connectionId}/sync-to-superset`, { method: 'POST' }),

    syncAllConnections: () =>
        apiFetch('/api/v1/analytics/sync-all-to-superset', { method: 'POST' }),

    getSampleQueries: (connectionId: number) =>
        apiFetch(`/api/v1/analytics/sample-queries/${connectionId}`),

    getSupersetStatus: (connectionId: number) =>
        apiFetch(`/api/v1/connections/${connectionId}/superset-status`),
};

export const settingsService = {
    getProfile: () => apiFetch<any>('/api/v1/settings/profile'),
    updateProfile: (data: any) =>
        apiFetch('/api/v1/settings/profile', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getUserSettings: () => apiFetch<any>('/api/v1/settings/user-settings'),
    updateUserSettings: (data: any) =>
        apiFetch('/api/v1/settings/user-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getConnectionSettings: () => apiFetch<any>('/api/v1/settings/connection-settings'),
    updateConnectionSettings: (data: any) =>
        apiFetch('/api/v1/settings/connection-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getETLSchedules: () => apiFetch<any>('/api/v1/settings/etl-schedules'),
    updateETLSchedule: (connectionId: number, data: any) =>
        apiFetch(`/api/v1/settings/etl-schedules/${connectionId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getAnalyticsSettings: () => apiFetch<any>('/api/v1/settings/analytics-settings'),
    updateAnalyticsSettings: (data: any) =>
        apiFetch('/api/v1/settings/analytics-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getNotificationSettings: () => apiFetch<any>('/api/v1/settings/notification-settings'),
    updateNotificationSettings: (data: any) =>
        apiFetch('/api/v1/settings/notification-settings', {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    getSystemInfo: () => apiFetch<any>('/api/v1/settings/system-info'),
};
