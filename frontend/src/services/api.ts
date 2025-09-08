/* eslint-disable @typescript-eslint/no-explicit-any */
import axios, { type AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

// Types
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

// API functions
export const authService = {
    login: (username: string, password: string) =>
        api.post('/api/v1/auth/login',
            new URLSearchParams({ username, password }),
            { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        ) as Promise<AxiosResponse<{ access_token: string }>>,

    register: (userData: {
        email: string;
        username: string;
        password: string;
        full_name?: string;
    }) => api.post('/api/v1/auth/register', userData),

    getCurrentUser: (): Promise<AxiosResponse<User>> =>
        api.get('/api/v1/auth/me') as Promise<AxiosResponse<User>>,
};

export const connectionService = {
    getConnections: (): Promise<AxiosResponse<DatabaseConnection[]>> =>
        api.get('/api/v1/connections/') as Promise<AxiosResponse<DatabaseConnection[]>>,

    createConnection: (connectionData: CreateConnectionRequest): Promise<AxiosResponse<DatabaseConnection>> =>
        api.post('/api/v1/connections/', connectionData) as Promise<AxiosResponse<DatabaseConnection>>,

    getConnection: (id: number): Promise<AxiosResponse<DatabaseConnection>> =>
        api.get(`/api/v1/connections/${id}`) as Promise<AxiosResponse<DatabaseConnection>>,

    updateConnection: (id: number, updateData: Partial<DatabaseConnection>) =>
        api.put(`/api/v1/connections/${id}`, updateData),

    deleteConnection: (id: number) =>
        api.delete(`/api/v1/connections/${id}`),

    testConnection: (id: number) =>
        api.post(`/api/v1/connections/${id}/test`),
};

export const jobService = {
    getJobs: (connectionId?: number): Promise<AxiosResponse<ETLJob>> =>
        api.get('/api/v1/jobs/', { params: connectionId ? { connection_id: connectionId } : {} }) as Promise<AxiosResponse<ETLJob>>,

    createJob: (jobData: { connection_id: number; job_type?: string }) =>
        api.post('/api/v1/jobs/', jobData),

    getJob: (id: number): Promise<AxiosResponse<ETLJob>> =>
        (api.get<ETLJob>(`/api/v1/jobs/${id}`) as Promise<AxiosResponse<ETLJob>>),

    triggerETLJob: (jobData: { connection_id: number; job_type?: string; trigger_type?: string }) =>
        api.post('/api/v1/jobs/trigger', jobData),

    triggerAllJobs: () =>
        api.post('/api/v1/jobs/trigger-all'),

    getSchedule: (connectionId: number) =>
        api.get(`/api/v1/jobs/connection/${connectionId}/schedule`),
};


export const analyticsService = {
    getSupersetInfo: (): Promise<AxiosResponse<any>> =>
        api.get('/api/v1/analytics/superset-info') as Promise<AxiosResponse<any>>,

    getConnectionsStatus: (): Promise<AxiosResponse<any>> =>
        api.get('/api/v1/analytics/connections-status') as Promise<AxiosResponse<any>>,

    syncConnectionToSuperset: (connectionId: number) =>
        api.post(`/api/v1/connections/${connectionId}/sync-to-superset`),

    syncAllConnections: () =>
        api.post('/api/v1/analytics/sync-all-to-superset'),

    getSampleQueries: (connectionId: number) =>
        api.get(`/api/v1/analytics/sample-queries/${connectionId}`),

    getSupersetStatus: (connectionId: number) =>
        api.get(`/api/v1/connections/${connectionId}/superset-status`),
};