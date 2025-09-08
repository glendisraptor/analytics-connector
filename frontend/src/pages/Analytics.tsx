/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { connectionService, analyticsService, type DatabaseConnection } from '../services/api';
import {
    ChartBarIcon,
    ExternalLinkIcon,
    RefreshCw,
    EyeIcon,
    CogIcon
} from 'lucide-react';
import { toast } from 'sonner';

const Analytics: React.FC = () => {
    const [syncingConnections, setSyncingConnections] = useState<Set<number>>(new Set());
    const queryClient = useQueryClient();

    // Get connections using TanStack Query
    const { data: connectionsResponse, isLoading } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    // Get analytics connections status
    const { data: analyticsStatus } = useQuery({
        queryKey: ['analytics-connections'],
        queryFn: () => analyticsService.getConnectionsStatus(),
        enabled: !!connectionsResponse?.data?.length
    });

    // Get Superset info
    const { data: supersetInfo } = useQuery({
        queryKey: ['superset-info'],
        queryFn: () => analyticsService.getSupersetInfo()
    });

    // Sync connection to Superset mutation
    const syncMutation = useMutation({
        mutationFn: async (connectionId: number) => analyticsService.syncConnectionToSuperset(connectionId),
        onSuccess: (data, connectionId) => {
            toast.success('Connection sync to Superset started!');
            setSyncingConnections(prev => new Set([...prev, connectionId]));

            console.log('Sync started for connection ID:', connectionId);
            console.log('Response data:', data);

            // Remove from syncing state after 10 seconds
            setTimeout(() => {
                setSyncingConnections(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(connectionId);
                    return newSet;
                });
                queryClient.invalidateQueries({ queryKey: ['analytics-connections'] });
                queryClient.invalidateQueries({ queryKey: ['connections'] });
            }, 10000);
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to sync connection');
        }
    });

    // Sync all connections mutation
    const syncAllMutation = useMutation({
        mutationFn: async () => {
            return analyticsService.syncAllConnections();
        },
        onSuccess: () => {
            toast.success('Started syncing all connections to Superset');
            queryClient.invalidateQueries({ queryKey: ['analytics-connections'] });
            queryClient.invalidateQueries({ queryKey: ['connections'] });
        },
        onError: (error: any) => {
            console.error(error);
            toast.error('Failed to sync connections');
        }
    });

    const handleSyncConnection = (connectionId: number) => {
        syncMutation.mutate(connectionId);
    };

    const handleSyncAll = () => {
        syncAllMutation.mutate();
    };

    // Process connections data
    const connections = connectionsResponse?.data || [];
    const connectedConnections = connections.filter((c: DatabaseConnection) => c.status === 'connected');
    const analyticsReadyConnections =
        analyticsStatus?.data?.connections?.filter((c: any) => c.analytics_ready) || [];

    // Get Superset URL from environment or use default
    const supersetUrl = import.meta.env.VITE_APP_SUPERSET_URL || supersetInfo?.superset_url || 'http://localhost:8088';

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
                    <p className="mt-2 text-gray-600">
                        Explore your data with powerful analytics and visualization tools
                    </p>
                </div>

                {connectedConnections.length > 0 && (
                    <div className="flex space-x-3">
                        <button
                            onClick={handleSyncAll}
                            disabled={syncAllMutation.isPending}
                            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                        >
                            <RefreshCw className="w-4 h-4 mr-2" />
                            {syncAllMutation.isPending ? 'Syncing...' : 'Sync All'}
                        </button>

                        <a
                            href={supersetUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                            Open Superset
                            <ExternalLinkIcon className="ml-2 w-4 h-4" />
                        </a>
                    </div>
                )}
            </div>

            {connectedConnections.length > 0 ? (
                <>
                    {/* Superset Quick Access */}
                    <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-medium">Apache Superset Analytics</h3>
                                <p className="mt-1 text-blue-100">
                                    Access your analytics platform to create dashboards and explore data
                                </p>
                            </div>
                            <ChartBarIcon className="w-12 h-12 text-blue-200" />
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                            <a
                                href={supersetInfo?.login_url || `${supersetUrl}/login/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-3 py-2 bg-gray-800 bg-opacity-20 rounded-md text-sm font-medium hover:bg-opacity-30"
                            >
                                Login to Superset
                                <ExternalLinkIcon className="ml-2 w-4 h-4" />
                            </a>

                            <a
                                href={supersetInfo?.sql_lab_url || `${supersetUrl}/sqllab/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-3 py-2 bg-gray-800 bg-opacity-20 rounded-md text-sm font-medium hover:bg-opacity-30"
                            >
                                SQL Lab
                                <ExternalLinkIcon className="ml-2 w-4 h-4" />
                            </a>

                            <a
                                href={supersetInfo?.dashboard_url || `${supersetUrl}/dashboard/list/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-3 py-2 bg-gray-800 bg-opacity-20 rounded-md text-sm font-medium hover:bg-opacity-30"
                            >
                                Dashboards
                                <ExternalLinkIcon className="ml-2 w-4 h-4" />
                            </a>
                        </div>

                        <div className="mt-4 text-sm text-blue-100">
                            <strong>Default Login:</strong> admin / admin
                        </div>
                    </div>

                    {/* Analytics Status */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <ChartBarIcon className="h-6 w-6 text-blue-500" />
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Total Connections
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {connections.length}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <EyeIcon className="h-6 w-6 text-green-500" />
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Analytics Ready
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {analyticsReadyConnections.length}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <CogIcon className="h-6 w-6 text-purple-500" />
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Superset Status
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {supersetInfo ? 'Online' : 'Offline'}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Connections List */}
                    <div className="bg-white shadow rounded-lg">
                        <div className="px-6 py-4 border-b border-gray-200">
                            <h3 className="text-lg font-medium text-gray-900">Database Connections</h3>
                            <p className="mt-1 text-sm text-gray-500">
                                Manage analytics for your database connections
                            </p>
                        </div>

                        <div className="divide-y divide-gray-200">
                            {connectedConnections.map((connection: DatabaseConnection) => {

                                return (
                                    <ConnectionAnalyticsCard
                                        key={connection.id}
                                        connection={{ ...connection, connection_id: connection.id }}
                                        onSync={handleSyncConnection}
                                        isSyncing={syncingConnections.has(connection.id)}
                                        supersetUrl={supersetUrl}
                                    />
                                );
                            })}
                        </div>
                    </div>
                </>
            ) : (
                /* Empty State */
                <div className="text-center py-12">
                    <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No analytics available</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Connect and sync your databases to start analyzing your data.
                    </p>
                    <div className="mt-6">
                        <a
                            href="/connections"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                            Set up your first connection
                        </a>
                    </div>
                </div>
            )}
        </div>
    );
};

// Connection Analytics Card Component
interface ConnectionAnalyticsCardProps {
    connection: DatabaseConnection & { connection_id: number };
    onSync: (connectionId: number) => void;
    isSyncing: boolean;
    supersetUrl?: string;
}

const ConnectionAnalyticsCard: React.FC<ConnectionAnalyticsCardProps> = ({
    connection,
    onSync,
    isSyncing,
    supersetUrl
}) => {
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'connected':
                return 'text-green-600 bg-green-100';
            case 'failed':
                return 'text-red-600 bg-red-100';
            default:
                return 'text-yellow-600 bg-yellow-100';
        }
    };

    return (
        <div className="px-6 py-4">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <div className="flex items-center">
                        <h4 className="text-sm font-medium text-gray-900">{connection.name}</h4>
                        <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(connection.status)}`}>
                            {connection.status}
                        </span>
                    </div>

                    <div className="mt-1 flex items-center text-sm text-gray-500">
                        <span className="capitalize">{connection.database_type}</span>
                        {connection.last_sync && (
                            <>
                                <span className="mx-2">•</span>
                                <span>Last sync: {new Date(connection.last_sync).toLocaleDateString()}</span>
                            </>
                        )}
                    </div>
                </div>

                <div className="flex items-center space-x-3">
                    {connection.analytics_ready ? (
                        <>
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Analytics Ready
                            </span>

                            {supersetUrl && (
                                <a
                                    href={`${supersetUrl}/sqllab/`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                                >
                                    <EyeIcon className="w-3 h-3 mr-1" />
                                    Explore Data
                                </a>
                            )}
                        </>
                    ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            Not Ready
                        </span>
                    )}

                    <button
                        onClick={() => onSync(connection.connection_id)}
                        disabled={isSyncing}
                        className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-blue-700 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`w-3 h-3 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
                        {isSyncing ? 'Syncing...' : 'Sync to Superset'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Analytics;