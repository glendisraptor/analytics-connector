import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { connectionService, jobService, type DatabaseConnection, type ETLJob } from '../services/api';
import { Link } from 'react-router-dom';
import {
    Database,
    CheckCircle,
    XCircle,
    Clock,
    BarChart3,
    Loader2,
    Plus
} from 'lucide-react';

const Dashboard: React.FC = () => {
    const { data: connections, isLoading: connectionsLoading } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    const { data: jobs, isLoading: jobsLoading } = useQuery({
        queryKey: ['recent-jobs'],
        queryFn: () => jobService.getJobs()
    });

    const connectionStats = {
        total: connections?.data?.length || 0,
        active: connections?.data?.filter((c: DatabaseConnection) => c.is_active && c.status === 'connected').length || 0,
        failed: connections?.data?.filter((c: DatabaseConnection) => c.status === 'failed').length || 0,
    };

    const recentJobs = jobs?.data?.slice(0, 5) || [];

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'failed':
                return <XCircle className="w-5 h-5 text-red-500" />;
            case 'running':
                return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
            default:
                return <Clock className="w-5 h-5 text-yellow-500" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'connected':
                return 'text-green-600 bg-green-100';
            case 'failed':
                return 'text-red-600 bg-red-100';
            case 'testing':
                return 'text-yellow-600 bg-yellow-100';
            default:
                return 'text-gray-600 bg-gray-100';
        }
    };

    if (connectionsLoading || jobsLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <p className="mt-2 text-gray-600">
                    Monitor your database connections and analytics pipelines
                </p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="p-5">
                        <div className="flex items-center">
                            <div className="flex-shrink-0">
                                <Database className="h-6 w-6 text-gray-400" />
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                        Total Connections
                                    </dt>
                                    <dd className="text-lg font-medium text-gray-900">
                                        {connectionStats.total}
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
                                <CheckCircle className="h-6 w-6 text-green-400" />
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                        Active Connections
                                    </dt>
                                    <dd className="text-lg font-medium text-gray-900">
                                        {connectionStats.active}
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
                                <BarChart3 className="h-6 w-6 text-blue-400" />
                            </div>
                            <div className="ml-5 w-0 flex-1">
                                <dl>
                                    <dt className="text-sm font-medium text-gray-500 truncate">
                                        Recent Jobs
                                    </dt>
                                    <dd className="text-lg font-medium text-gray-900">
                                        {recentJobs.length}
                                    </dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                        Quick Actions
                    </h3>
                    <div className="flex flex-wrap gap-4">
                        <Link
                            to="/connections"
                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                            <Database className="w-4 h-4 mr-2" />
                            Manage Connections
                        </Link>
                        <Link
                            to="/analytics"
                            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                        >
                            <BarChart3 className="w-4 h-4 mr-2" />
                            View Analytics
                        </Link>
                    </div>
                </div>
            </div>

            {/* Recent Connections and Jobs */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Connections */}
                <div className="bg-white shadow rounded-lg">
                    <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">
                            Recent Connections
                        </h3>
                    </div>
                    <div className="divide-y divide-gray-200">
                        {connections?.data?.slice(0, 5).map((connection: DatabaseConnection) => (
                            <div key={connection.id} className="px-4 py-4 flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 truncate">
                                        {connection.name}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        {connection.database_type} • Created {new Date(connection.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <div className="flex-shrink-0">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(connection.status)}`}>
                                        {connection.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                        {(!connections?.data || connections.data.length === 0) && (
                            <div className="text-center py-12">
                                <Database className="mx-auto h-12 w-12 text-gray-400" />
                                <h3 className="mt-2 text-sm font-medium text-gray-900">No connections</h3>
                                <p className="mt-1 text-sm text-gray-500">
                                    Get started by creating your first database connection.
                                </p>
                                <div className="mt-6">
                                    <Link
                                        to={"/connections"}
                                        className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-gray-600 hover:bg-gray-700"
                                    >
                                        <Plus className="w-4 h-4 mr-2" />
                                        Add Connection
                                    </Link>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Recent Jobs */}
                <div className="bg-white shadow rounded-lg">
                    <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">
                            Recent Jobs
                        </h3>
                    </div>
                    <div className="divide-y divide-gray-200">
                        {recentJobs.map((job: ETLJob) => (
                            <div key={job.id} className="px-4 py-4 flex items-center justify-between">
                                <div className="flex items-center">
                                    {getStatusIcon(job.status)}
                                    <div className="ml-3">
                                        <p className="text-sm font-medium text-gray-900">
                                            {job.job_type}
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            {job.records_processed} records • {new Date(job.created_at).toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex-shrink-0">
                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                                        {job.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                        {recentJobs.length === 0 && (
                            <div className="px-4 py-8 text-center text-gray-500">
                                No jobs found. ETL jobs will appear here once you start syncing data.
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;