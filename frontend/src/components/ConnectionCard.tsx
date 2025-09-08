
import React from 'react';
import type { DatabaseConnection } from '../services/api';
import { CheckCircleIcon, ClockIcon, PencilIcon, TrashIcon, Wrench, XCircleIcon } from 'lucide-react';
import ETLJobManager from './ETLJobManager';

interface ConnectionCardProps {
    connection: DatabaseConnection;
    onEdit: (connection: DatabaseConnection) => void;
    onDelete: (id: number) => void;
    onTest: (id: number) => void;
    isDeleting: boolean;
    isTesting: boolean;
}

const ConnectionCard: React.FC<ConnectionCardProps> = ({
    connection,
    onEdit,
    onDelete,
    onTest,
    isDeleting,
    isTesting,
}) => {
    const getStatusIcon = () => {
        switch (connection.status) {
            case 'connected':
                return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
            case 'failed':
                return <XCircleIcon className="w-5 h-5 text-red-500" />;
            case 'testing':
                return <div className="w-5 h-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />;
            default:
                return <ClockIcon className="w-5 h-5 text-yellow-500" />;
        }
    };

    const getStatusColor = () => {
        switch (connection.status) {
            case 'connected':
                return 'text-green-600 bg-green-100';
            case 'failed':
                return 'text-red-600 bg-red-100';
            case 'testing':
                return 'text-blue-600 bg-blue-100';
            default:
                return 'text-yellow-600 bg-yellow-100';
        }
    };

    const getDatabaseIcon = () => {
        const iconClass = "w-8 h-8 text-gray-600";
        switch (connection.database_type) {
            case 'postgresql':
                return <div className={`${iconClass} bg-blue-100 rounded p-1`}>🐘</div>;
            case 'mysql':
                return <div className={`${iconClass} bg-orange-100 rounded p-1`}>🐬</div>;
            case 'mongodb':
                return <div className={`${iconClass} bg-green-100 rounded p-1`}>🍃</div>;
            case 'sqlite':
                return <div className={`${iconClass} bg-gray-100 rounded p-1`}>🗃️</div>;
            default:
                return <div className={`${iconClass} bg-gray-100 rounded p-1`}>💾</div>;
        }
    };

    return (
        <div className="bg-white shadow rounded-lg overflow-hidden">
            <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                        {getDatabaseIcon()}
                        <div className="ml-3">
                            <h3 className="text-lg font-medium text-gray-900">{connection.name}</h3>
                            <p className="text-sm text-gray-500 capitalize">
                                {connection.database_type.replace('_', ' ')}
                            </p>
                        </div>
                    </div>
                    {getStatusIcon()}
                </div>

                {connection.status === 'connected' && (
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                        <ETLJobManager
                            connectionId={connection.id}
                            connectionName={connection.name}
                            connectionStatus={connection.status}
                        />
                    </div>
                )}

                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Status</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor()}`}>
                            {connection.status}
                        </span>
                    </div>

                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Sync Frequency</span>
                        <span className="text-sm text-gray-900 capitalize">{connection.sync_frequency}</span>
                    </div>

                    {connection.last_sync && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-500">Last Sync</span>
                            <span className="text-sm text-gray-900">
                                {new Date(connection.last_sync).toLocaleDateString()}
                            </span>
                        </div>
                    )}

                    {connection.last_tested && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-500">Last Tested</span>
                            <span className="text-sm text-gray-900">
                                {new Date(connection.last_tested).toLocaleDateString()}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-gray-50 px-6 py-3 flex justify-between">
                <div className="flex space-x-2">
                    <button
                        onClick={() => onTest(connection.id)}
                        disabled={isTesting || connection.status === 'testing'}
                        className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Wrench className="w-3 h-3 mr-1" />
                        {connection.status === 'testing' ? 'Testing...' : 'Test'}
                    </button>
                    <button
                        onClick={() => onEdit(connection)}
                        className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                    >
                        <PencilIcon className="w-3 h-3 mr-1" />
                        Edit
                    </button>
                </div>
                <button
                    onClick={() => onDelete(connection.id)}
                    disabled={isDeleting}
                    className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    <TrashIcon className="w-3 h-3 mr-1" />
                    {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
            </div>
        </div>
    );
};

export default ConnectionCard;