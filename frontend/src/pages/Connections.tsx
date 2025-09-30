import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { connectionService, type DatabaseConnection } from '../services/api';
import { Plus, Database, Loader2, Play, Eye, Edit, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import ConnectionFormDialog from '../components/ConnectionFormDialog';

const Connections: React.FC = () => {
    const [showForm, setShowForm] = useState(false);
    const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null);
    const queryClient = useQueryClient();

    const { data: connections, isLoading } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => connectionService.deleteConnection(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['connections'] });
            toast.success('Connection deleted successfully');
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to delete connection');
        },
    });

    const testMutation = useMutation({
        mutationFn: (id: number) => connectionService.testConnection(id),
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

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'connected':
                return "bg-success/20 text-success border-success/30";
            case 'failed':
                return "bg-destructive/20 text-destructive border-destructive/30";
            case 'testing':
                return "bg-warning/20 text-warning border-warning/30";
            default:
                return "bg-muted/20 text-muted-foreground border-muted/30";
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
        );
    }

    const connectionsList = connections?.data || [];

    return (
        <>
            <div className="p-6">
                <div className="max-w-7xl mx-auto space-y-8">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <div>
                            <h1 className="text-3xl font-bold text-foreground">Database Connections</h1>
                            <p className="text-muted-foreground">Manage your database connections and sync settings</p>
                        </div>
                        <Button 
                            onClick={() => setShowForm(true)}
                            className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated"
                        >
                            <Plus className="w-4 h-4 mr-2" />
                            Add Connection
                        </Button>
                    </div>

                    {/* Connections List */}
                    {connectionsList.length > 0 ? (
                        <div className="space-y-6">
                            {connectionsList.map((connection: DatabaseConnection) => (
                                <Card key={connection.id} className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 bg-gradient-accent rounded-lg flex items-center justify-center">
                                                    <Database className="w-6 h-6 text-white" />
                                                </div>
                                                <div>
                                                    <CardTitle className="text-xl text-foreground">{connection.name}</CardTitle>
                                                    <CardDescription className="text-muted-foreground">
                                                        {connection.database_type}
                                                    </CardDescription>
                                                </div>
                                            </div>
                                            <Badge className={getStatusBadgeClass(connection.status)}>
                                                <div className={`w-2 h-2 rounded-full mr-2 ${
                                                    connection.status === 'connected' ? 'bg-success' :
                                                    connection.status === 'failed' ? 'bg-destructive' :
                                                    'bg-warning'
                                                }`}></div>
                                                {connection.status}
                                            </Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-6">
                                        {/* Connection Details */}
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium text-foreground">Status</p>
                                                <p className={`text-sm ${
                                                    connection.status === 'connected' ? 'text-success' :
                                                    connection.status === 'failed' ? 'text-destructive' :
                                                    'text-warning'
                                                }`}>
                                                    {connection.status}
                                                </p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium text-foreground">Sync Frequency</p>
                                                <p className="text-sm text-muted-foreground">{connection.sync_frequency}</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium text-foreground">Last Sync</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {connection.last_sync ? new Date(connection.last_sync).toLocaleString() : 'Never'}
                                                </p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium text-foreground">Last Tested</p>
                                                <p className="text-sm text-muted-foreground">
                                                    {connection.last_tested ? new Date(connection.last_tested).toLocaleString() : 'Never'}
                                                </p>
                                            </div>
                                        </div>

                                        {/* Sync Settings */}
                                        <div className="bg-muted/30 rounded-lg p-4 border border-border/40">
                                            <div className="flex items-center justify-between mb-4">
                                                <h4 className="font-medium text-foreground">Sync Settings</h4>
                                                <div className="flex items-center gap-2">
                                                    <Button size="sm" className="bg-gradient-primary text-primary-foreground hover:opacity-90">
                                                        <Play className="w-4 h-4 mr-2" />
                                                        Sync Data
                                                    </Button>
                                                    <Button size="sm" variant="outline" className="border-border hover:bg-muted/50">
                                                        <Eye className="w-4 h-4 mr-2" />
                                                        Show Jobs
                                                    </Button>
                                                </div>
                                            </div>
                                            <div className="text-sm text-muted-foreground">
                                                {connection.sync_frequency} sync • Analytics Ready: {connection.analytics_ready ? 'Yes' : 'No'}
                                            </div>
                                        </div>

                                        {/* Action Buttons */}
                                        <div className="flex items-center gap-3 pt-4 border-t border-border/40">
                                            <Button 
                                                size="sm" 
                                                variant="outline" 
                                                className="border-border hover:bg-muted/50"
                                                onClick={() => handleTest(connection.id)}
                                                disabled={testMutation.isPending}
                                            >
                                                <Database className="w-4 h-4 mr-2" />
                                                Test
                                            </Button>
                                            <Button 
                                                size="sm" 
                                                variant="outline" 
                                                className="border-border hover:bg-muted/50"
                                                onClick={() => handleEdit(connection)}
                                            >
                                                <Edit className="w-4 h-4 mr-2" />
                                                Edit
                                            </Button>
                                            <Button 
                                                size="sm" 
                                                variant="destructive" 
                                                className="bg-destructive/20 text-destructive hover:bg-destructive/30 border-destructive/30"
                                                onClick={() => handleDelete(connection.id)}
                                                disabled={deleteMutation.isPending}
                                            >
                                                <Trash2 className="w-4 h-4 mr-2" />
                                                Delete
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        /* Empty State */
                        <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                            <CardContent className="flex flex-col items-center justify-center py-12">
                                <div className="w-16 h-16 bg-gradient-accent rounded-full flex items-center justify-center mb-4">
                                    <Database className="w-8 h-8 text-white" />
                                </div>
                                <h3 className="text-lg font-semibold text-foreground mb-2">No connections yet</h3>
                                <p className="text-muted-foreground text-center mb-6">
                                    Get started by creating your first database connection
                                </p>
                                <Button 
                                    onClick={() => setShowForm(true)}
                                    className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated"
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    Add Your First Connection
                                </Button>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>

            {/* Connection Form Dialog */}
            {showForm && (
                <ConnectionFormDialog
                    connection={editingConnection}
                    onClose={handleCloseForm}
                    onSuccess={handleFormSuccess}
                />
            )}
        </>
    );
};

export default Connections;