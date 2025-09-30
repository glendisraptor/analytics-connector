/* eslint-disable @typescript-eslint/no-explicit-any */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobService, connectionService, type ETLJob, type DatabaseConnection } from '../services/api';
import {
    Clock,
    CheckCircle,
    XCircle,
    GitBranch,
    Loader2,
    RefreshCw,
    Database,
    Activity
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const ETLDashboard: React.FC = () => {
    const queryClient = useQueryClient();

    const { data: connections } = useQuery({
        queryKey: ['connections'],
        queryFn: () => connectionService.getConnections()
    });

    const { data: allJobs, isLoading } = useQuery({
        queryKey: ['all-jobs'],
        queryFn: () => jobService.getJobs(),
        refetchInterval: 10000
    });

    const triggerAllMutation = useMutation({
        mutationFn: async () => jobService.triggerAllJobs(),
        onSuccess: () => {
            toast.success('Started ETL jobs for all connections');
            queryClient.invalidateQueries({ queryKey: ['all-jobs'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to trigger jobs');
        }
    });

    const connectedConnections = connections?.data?.filter(
        (c: DatabaseConnection) => c.status === 'connected'
    ) || [];

    const jobsData = allJobs?.data || [];
    
    const runningJobs = jobsData.filter(
        (job: ETLJob) => ['pending', 'running'].includes(job.status)
    );

    const todayJobs = jobsData.filter((job: ETLJob) => {
        const today = new Date().toDateString();
        return new Date(job.created_at).toDateString() === today;
    });

    const totalRecords = jobsData.reduce((total: number, job: ETLJob) =>
        total + (job.records_processed || 0), 0
    );

    const stats = [
        {
            title: "Active Connections",
            value: connectedConnections.length,
            icon: Database,
            color: "bg-gradient-accent"
        },
        {
            title: "Running Jobs",
            value: runningJobs.length,
            icon: Activity,
            color: "bg-gradient-secondary"
        },
        {
            title: "Today's Jobs",
            value: todayJobs.length,
            icon: Clock,
            color: "bg-gradient-primary"
        },
        {
            title: "Total Records",
            value: totalRecords.toLocaleString(),
            icon: GitBranch,
            color: "bg-gradient-accent"
        }
    ];

    const getJobStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-5 h-5 text-success" />;
            case 'failed':
                return <XCircle className="w-5 h-5 text-destructive" />;
            case 'running':
                return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
            default:
                return <Clock className="w-5 h-5 text-warning" />;
        }
    };

    const getJobStatusBadge = (status: string) => {
        switch (status) {
            case 'completed':
                return "bg-success/20 text-success border-success/30";
            case 'failed':
                return "bg-destructive/20 text-destructive border-destructive/30";
            case 'running':
                return "bg-primary/20 text-primary border-primary/30";
            default:
                return "bg-warning/20 text-warning border-warning/30";
        }
    };

    const getConnectionName = (connectionId: number) => {
        const connection = connections?.data?.find((c: DatabaseConnection) => c.id === connectionId);
        return connection?.name || `Connection ${connectionId}`;
    };

    const recentJobs = jobsData.slice(0, 10);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">ETL Jobs Dashboard</h1>
                        <p className="text-muted-foreground">Manage data synchronization across all connections</p>
                    </div>
                    <Button 
                        className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated"
                        onClick={() => triggerAllMutation.mutate()}
                        disabled={triggerAllMutation.isPending || connectedConnections.length === 0}
                    >
                        <RefreshCw className={`w-4 h-4 mr-2 ${triggerAllMutation.isPending ? 'animate-spin' : ''}`} />
                        {triggerAllMutation.isPending ? 'Syncing...' : 'Sync All Data'}
                    </Button>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {stats.map((stat, index) => (
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

                {/* Recent ETL Jobs */}
                <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="text-foreground">Recent ETL Jobs</CardTitle>
                                <CardDescription>Latest synchronization activities across all connections</CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {recentJobs.length > 0 ? (
                            <div className="space-y-3">
                                {recentJobs.map((job: ETLJob) => (
                                    <div 
                                        key={job.id} 
                                        className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/40 hover:bg-muted/50 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 bg-gradient-accent rounded-lg flex items-center justify-center">
                                                {getJobStatusIcon(job.status)}
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <p className="font-semibold text-foreground">
                                                        {getConnectionName(job.connection_id)}
                                                    </p>
                                                    <div className={`w-2 h-2 rounded-full ${
                                                        job.status === 'completed' ? 'bg-success' :
                                                        job.status === 'failed' ? 'bg-destructive' :
                                                        job.status === 'running' ? 'bg-primary' :
                                                        'bg-warning'
                                                    }`}></div>
                                                </div>
                                                <p className="text-sm text-muted-foreground">
                                                    {job.job_type} • {new Date(job.created_at).toLocaleString()}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <Badge className={`${getJobStatusBadge(job.status)} mb-1`}>
                                                    {job.status}
                                                </Badge>
                                                <p className="text-sm text-muted-foreground">
                                                    {job.records_processed.toLocaleString()} records
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-12">
                                <GitBranch className="mx-auto h-12 w-12 text-muted-foreground/50 mb-2" />
                                <p className="text-sm text-muted-foreground">
                                    No ETL jobs found. Click "Sync All Data" to start synchronization.
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ETLDashboard;