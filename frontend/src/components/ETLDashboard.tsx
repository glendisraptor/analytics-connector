import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobService, connectionService, type ETLJob, type DatabaseConnection } from '../services/api';
import {
    Play,
    Clock,
    CheckCircle,
    XCircle,
    ArrowBigDown,
    Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ETLDashboard: React.FC = () => {
    const queryClient = useQueryClient();

    // Get all connections
    const { data: connections } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    // Get all recent jobs
    const { data: allJobs, isLoading } = useQuery({
        queryKey: ['all-jobs'],
        queryFn: () => jobService.getJobs(),
        refetchInterval: 10000 // Refresh every 10 seconds
    });

    // Trigger all jobs mutation
    const triggerAllMutation = useMutation({
        mutationFn: async () => jobService.triggerAllJobs(),
        onSuccess: (data) => {
            console.log("Triggered all jobs:", data);
            toast.success(`Started TODO ETL jobs`);
            queryClient.invalidateQueries({ queryKey: ['all-jobs'] });
        },
        onError: (error) => {
            console.error("Error triggering all jobs:", error);
            toast.error('Failed to trigger jobs');
        }
    });

    const connectedConnections = connections?.data?.filter(
        (c: DatabaseConnection) => c.status === 'connected'
    ) || [];

    const runningJobs = allJobs?.data?.filter(
        (job: ETLJob) => ['pending', 'running'].includes(job.status)
    ) || [];

    const todayJobs = allJobs?.data?.filter((job: ETLJob) => {
        const today = new Date().toDateString();
        return new Date(job.created_at).toDateString() === today;
    }) || [];

    const totalRecords = allJobs?.data?.reduce((total: number, job: ETLJob) =>
        total + (job.records_processed || 0), 0
    ) || 0;

    const getJobStatusIcon = (status: string) => {
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

    const getJobStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'text-green-700 bg-green-50 border-green-200';
            case 'failed':
                return 'text-red-700 bg-red-50 border-red-200';
            case 'running':
                return 'text-blue-700 bg-blue-50 border-blue-200';
            default:
                return 'text-yellow-700 bg-yellow-50 border-yellow-200';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">ETL Jobs Dashboard</h2>
                    <p className="text-muted-foreground">Manage data synchronization across all connections</p>
                </div>

                <Button
                    onClick={() => triggerAllMutation.mutate()}
                    disabled={connectedConnections.length === 0 || triggerAllMutation.isPending}
                    className="gap-2"
                >
                    {triggerAllMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Play className="w-4 h-4" />
                    )}
                    {triggerAllMutation.isPending ? 'Starting...' : 'Sync All Data'}
                </Button>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Connected DBs</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{connectedConnections.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Running Jobs</CardTitle>
                        <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{runningJobs.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Jobs Today</CardTitle>
                        <CheckCircle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{todayJobs.length}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Records Synced</CardTitle>
                        <ArrowBigDown className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{totalRecords.toLocaleString()}</div>
                    </CardContent>
                </Card>
            </div>

            {/* Recent Jobs */}
            <Card>
                <CardHeader>
                    <CardTitle>Recent ETL Jobs</CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-8 w-8 animate-spin" />
                            <span className="ml-2 text-muted-foreground">Loading jobs...</span>
                        </div>
                    ) : allJobs?.data?.length > 0 ? (
                        <div className="space-y-4">
                            {allJobs.data.slice(0, 10).map((job: ETLJob) => {
                                const connection = connections?.data?.find((c: DatabaseConnection) => c.id === job.connection_id);
                                return (
                                    <div key={job.id} className="flex items-center justify-between p-4 border rounded-lg">
                                        <div className="flex items-center space-x-4">
                                            {getJobStatusIcon(job.status)}
                                            <div>
                                                <div className="font-medium">
                                                    {connection?.name || `Connection ${job.connection_id}`}
                                                </div>
                                                <div className="text-sm text-muted-foreground">
                                                    {job.job_type.replace('_', ' ')} • Started {new Date(job.created_at).toLocaleString()}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right space-y-1">
                                            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getJobStatusColor(job.status)}`}>
                                                {job.status}
                                            </div>
                                            {job.records_processed > 0 && (
                                                <div className="text-sm text-muted-foreground">
                                                    {job.records_processed.toLocaleString()} records
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            No ETL jobs found. Connect a database and start syncing data.
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default ETLDashboard;