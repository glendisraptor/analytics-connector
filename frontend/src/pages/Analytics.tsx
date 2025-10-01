/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BarChart3, RefreshCw, ExternalLink, Database, Eye, Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import type { DatabaseConnection } from '@/types';
import { connectionService, supersetService } from '@/services/api';

const Analytics: React.FC = () => {
    const [syncingConnections, setSyncingConnections] = useState<Set<number>>(new Set());
    const queryClient = useQueryClient();

    const { data: connectionsResponse, isLoading } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    const { data: analyticsStatus } = useQuery({
        queryKey: ['analytics-connections'],
        queryFn: () => supersetService.getStatus(),
        enabled: !!connectionsResponse?.length
    });

    const { data: supersetInfo } = useQuery({
        queryKey: ['superset-info'],
        queryFn: () => supersetService.getInfo()
    });

    const syncMutation = useMutation({
        mutationFn: async (connectionId: number) => supersetService.syncConnection(connectionId),
        onSuccess: (_data, connectionId) => {
            toast.success('Connection sync to Superset started!');
            setSyncingConnections(prev => new Set([...prev, connectionId]));

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

    const syncAllMutation = useMutation({
        mutationFn: async () => supersetService.syncAllConnections(),
        onSuccess: () => {
            toast.success('Started syncing all connections to Superset');
            queryClient.invalidateQueries({ queryKey: ['analytics-connections'] });
            queryClient.invalidateQueries({ queryKey: ['connections'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to sync connections');
        }
    });

    const handleSyncConnection = (connectionId: number) => {
        syncMutation.mutate(connectionId);
    };

    const handleSyncAll = () => {
        syncAllMutation.mutate();
    };

    const connections = connectionsResponse || [];
    const connectedConnections = connections.filter((c: DatabaseConnection) => c.status === 'connected');
    const analyticsReadyConnections = analyticsStatus?.connections?.filter((c: any) => c.analytics_ready) || [];

    const supersetUrl = import.meta.env.VITE_APP_SUPERSET_URL || supersetInfo?.superset_url || 'http://localhost:8088';

    const analytics = [
        {
            title: "Total Connections",
            value: connections.length,
            icon: Database,
            color: "bg-gradient-accent"
        },
        {
            title: "Analytics Ready",
            value: analyticsReadyConnections.length,
            icon: Eye,
            color: "bg-gradient-secondary"
        },
        {
            title: "Superset Status",
            value: supersetInfo?.connection_status === 'connected' ? "Online" : "Offline",
            icon: Zap,
            color: "bg-gradient-primary"
        }
    ];

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
        );
    }

    if (connectedConnections.length === 0) {
        return (
            <div className="p-6">
                <div className="max-w-7xl mx-auto">
                    <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                        <CardContent className="flex flex-col items-center justify-center py-12">
                            <div className="w-16 h-16 bg-gradient-primary rounded-full flex items-center justify-center mb-4">
                                <BarChart3 className="w-8 h-8 text-white" />
                            </div>
                            <h3 className="text-lg font-semibold text-foreground mb-2">No analytics available</h3>
                            <p className="text-muted-foreground text-center mb-6">
                                Connect and sync your databases to start analyzing your data.
                            </p>
                            <Button asChild className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated">
                                <Link to="/connections">
                                    <Database className="w-4 h-4 mr-2" />
                                    Set up your first connection
                                </Link>
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">Analytics Dashboard</h1>
                        <p className="text-muted-foreground">Explore your data with powerful analytics and visualization tools</p>
                    </div>
                    <div className="flex gap-3">
                        <Button
                            variant="outline"
                            className="border-border hover:bg-muted/50"
                            onClick={handleSyncAll}
                            disabled={syncAllMutation.isPending}
                        >
                            <RefreshCw className={`w-4 h-4 mr-2 ${syncAllMutation.isPending ? 'animate-spin' : ''}`} />
                            {syncAllMutation.isPending ? 'Syncing...' : 'Sync All'}
                        </Button>
                        <Button
                            asChild
                            className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated"
                        >
                            <a href={supersetUrl} target="_blank" rel="noopener noreferrer">
                                <ExternalLink className="w-4 h-4 mr-2" />
                                Open Superset
                            </a>
                        </Button>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {analytics.map((stat, index) => (
                        <Card key={index} className="relative overflow-hidden bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                            <CardHeader className="pb-2">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-sm font-medium text-muted-foreground">
                                        {stat.title}
                                    </CardTitle>
                                    <div className={`w-8 h-8 rounded-lg ${stat.color} flex items-center justify-center`}>
                                        <stat.icon className="w-4 h-4 text-white" />
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-3xl font-bold text-foreground">{stat.value}</div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Apache Superset Section */}
                <Card className="bg-gradient-primary text-primary-foreground shadow-elevated">
                    <CardHeader className="pb-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                                    <BarChart3 className="w-6 h-6 text-white" />
                                </div>
                                <div>
                                    <CardTitle className="text-xl text-white">Apache Superset Analytics</CardTitle>
                                    <CardDescription className="text-primary-foreground/80">
                                        Access your analytics platform to create dashboards and explore data
                                    </CardDescription>
                                </div>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex flex-wrap gap-3">
                            <Button
                                asChild
                                variant="secondary"
                                className="bg-white/10 text-white border-white/20 hover:bg-white/20"
                            >
                                <a href={`${supersetUrl}/login/`} target="_blank" rel="noopener noreferrer">
                                    <ExternalLink className="w-4 h-4 mr-2" />
                                    Login to Superset
                                </a>
                            </Button>
                            <Button
                                asChild
                                variant="secondary"
                                className="bg-white/10 text-white border-white/20 hover:bg-white/20"
                            >
                                <a href={`${supersetUrl}/sqllab/`} target="_blank" rel="noopener noreferrer">
                                    <BarChart3 className="w-4 h-4 mr-2" />
                                    SQL Lab
                                </a>
                            </Button>
                            <Button
                                asChild
                                variant="secondary"
                                className="bg-white/10 text-white border-white/20 hover:bg-white/20"
                            >
                                <a href={`${supersetUrl}/dashboard/list/`} target="_blank" rel="noopener noreferrer">
                                    <Database className="w-4 h-4 mr-2" />
                                    Dashboards
                                </a>
                            </Button>
                        </div>
                        <div className="text-sm text-primary-foreground/80">
                            <strong>Default Login:</strong> admin / admin
                        </div>
                    </CardContent>
                </Card>

                {/* Database Connections */}
                <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                    <CardHeader>
                        <CardTitle className="text-foreground">Database Connections</CardTitle>
                        <CardDescription>Manage analytics for your database connections</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {connectedConnections.map((connection: DatabaseConnection) => (
                                <div key={connection.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/40">
                                    <div className="flex items-center gap-4">
                                        <div className="w-12 h-12 bg-gradient-accent rounded-lg flex items-center justify-center">
                                            <Database className="w-6 h-6 text-white" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground">{connection.name}</p>
                                            <p className="text-sm text-muted-foreground">
                                                {connection.database_type} • Last sync: {connection.last_sync ? new Date(connection.last_sync).toLocaleString() : 'Never'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Badge className={
                                            connection.analytics_ready
                                                ? "bg-success/20 text-success border-success/30"
                                                : "bg-muted/20 text-muted-foreground border-muted/30"
                                        }>
                                            {connection.analytics_ready ? 'Ready' : 'Not Synced'}
                                        </Badge>
                                        <div className="flex gap-2">
                                            <Button
                                                asChild
                                                size="sm"
                                                className="bg-gradient-secondary text-secondary-foreground hover:opacity-90"
                                            >
                                                <a href={`${supersetUrl}/sqllab/`} target="_blank" rel="noopener noreferrer">
                                                    <Eye className="w-4 h-4 mr-2" />
                                                    Explore Data
                                                </a>
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="border-border hover:bg-muted/50"
                                                onClick={() => handleSyncConnection(connection.id)}
                                                disabled={syncingConnections.has(connection.id)}
                                            >
                                                <RefreshCw className={`w-4 h-4 mr-2 ${syncingConnections.has(connection.id) ? 'animate-spin' : ''}`} />
                                                {syncingConnections.has(connection.id) ? 'Syncing...' : 'Sync to Superset'}
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default Analytics;