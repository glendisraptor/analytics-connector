/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { connectionService, type DatabaseConnection } from '../services/api';
import ConnectionForm from '../components/ConnectionForm';
import ConnectionCard from '../components/ConnectionCard';
import { Plus, Database, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const Connections: React.FC = () => {
    const [showForm, setShowForm] = useState(false);
    const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null);
    const queryClient = useQueryClient();

    const { data: connections, isLoading } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => Promise.resolve(connectionService.deleteConnection(id)),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['connections'] });
            toast.success('Connection deleted successfully');
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to delete connection');
        },
    });

    const testMutation = useMutation({
        mutationFn: (id: number) => Promise.resolve(connectionService.testConnection(id)),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['connections'] });
            toast.success('Connection test started');
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to test connection');
        },
    });

    const handleEdit = (connection: DatabaseConnection) => {
        setEditingConnection(connection);
        setShowForm(true);
    };

    const handleDelete = (id: number) => {
        if (window.confirm('Are you sure you want to delete this connection?')) {
            deleteMutation.mutate(id);
        }
    };

    const handleTest = (id: number) => {
        testMutation.mutate(id);
    };

    const handleCloseForm = () => {
        setShowForm(false);
        setEditingConnection(null);
    };

    const handleFormSuccess = () => {
        setShowForm(false);
        setEditingConnection(null);
        queryClient.invalidateQueries({ queryKey: ['connections'] });
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Database Connections</h1>
                    <p className="mt-2 text-gray-600">
                        Manage your database connections and sync settings
                    </p>
                </div>
                <button
                    onClick={() => setShowForm(true)}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Connection
                </button>
            </div>

            {/* Connection Form Modal */}
            {showForm && (
                <ConnectionForm
                    connection={editingConnection}
                    onClose={handleCloseForm}
                    onSuccess={handleFormSuccess}
                />
            )}

            {/* Connections Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {connections?.data?.map((connection: DatabaseConnection) => (
                    <ConnectionCard
                        key={connection.id}
                        connection={connection}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                        onTest={handleTest}
                        isDeleting={deleteMutation.isPending}
                        isTesting={testMutation.isPending}
                    />
                ))}
            </div>

            {/* Empty State */}
            {(!connections?.data || connections.data.length === 0) && (
                <div className="text-center py-12">
                    <Database className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No connections</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        Get started by creating your first database connection.
                    </p>
                    <div className="mt-6">
                        <button
                            onClick={() => setShowForm(true)}
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                        >
                            <Plus className="w-4 h-4 mr-2" />
                            Add Connection
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Connections;