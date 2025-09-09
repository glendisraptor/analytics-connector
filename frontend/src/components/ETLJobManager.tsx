/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    Play,
    Clock,
    CheckCircle,
    XCircle,
    Calendar,
    Loader2,
    ChevronDown,
    ChevronUp
} from 'lucide-react';
import { jobService } from '../services/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface ETLJobManagerProps {
    connectionId: number;
    connectionName: string;
    connectionStatus: string;
}

interface ScheduleInfo {
    sync_frequency: string;
    next_scheduled_sync: string;
}

const ETLJobManager: React.FC<ETLJobManagerProps> = ({
    connectionId,
    connectionStatus
}) => {
    const [showJobs, setShowJobs] = useState(false);
    const queryClient = useQueryClient();

    // Get jobs for this connection
    const { data: jobs, isLoading: jobsLoading } = useQuery({
        queryKey: ['jobs', connectionId],
        queryFn: async () => {
            const response = await jobService.getJobs(connectionId);
            return response.data;
        },
        refetchInterval: 5000, // Refresh every 5 seconds
        enabled: showJobs
    });

    // Get ETL schedule info
    const { data: scheduleInfo } = useQuery<ScheduleInfo>({
        queryKey: ['schedule', connectionId],
        queryFn: async () => {
            const response = await jobService.getSchedule(connectionId);
            return response.data as ScheduleInfo;
        },
        enabled: showJobs,
    });


    // Trigger ETL job mutation
    const triggerJobMutation = useMutation({
        mutationFn: async () => jobService.triggerETLJob({
            connection_id: connectionId,
            job_type: 'full_sync',
            trigger_type: 'manual'
        }),
        onSuccess: () => {
            toast.success('ETL job started successfully!');
            queryClient.invalidateQueries({ queryKey: ['jobs', connectionId] });
            queryClient.invalidateQueries({ queryKey: ['connections'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to start ETL job');
        }
    });

    const getJobStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-4 h-4 text-green-500" />;
            case 'failed':
                return <XCircle className="w-4 h-4 text-red-500" />;
            case 'running':
                return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
            case 'pending':
                return <Clock className="w-4 h-4 text-yellow-500" />;
            default:
                return <Clock className="w-4 h-4 text-muted-foreground" />;
        }
    };

    const getJobStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
        switch (status) {
            case 'completed':
                return 'default';
            case 'failed':
                return 'destructive';
            case 'running':
                return 'secondary';
            case 'pending':
                return 'outline';
            default:
                return 'outline';
        }
    };

    const canTriggerJob = connectionStatus === 'connected';
    const hasRunningJob = jobs?.data?.some((job: any) => ['pending', 'running'].includes(job.status));

    return (
        <div className="space-y-4">
            {/* ETL Controls */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Button
                        onClick={() => triggerJobMutation.mutate()}
                        disabled={!canTriggerJob || hasRunningJob || triggerJobMutation.isPending}
                        size="sm"
                        className="gap-2"
                    >
                        {triggerJobMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Play className="w-4 h-4" />
                        )}
                        {triggerJobMutation.isPending ? 'Starting...' : 'Sync Data'}
                    </Button>

                    <Collapsible open={showJobs} onOpenChange={setShowJobs}>
                        <CollapsibleTrigger asChild>
                            <Button variant="outline" size="sm" className="gap-2">
                                <Calendar className="w-4 h-4" />
                                {showJobs ? 'Hide' : 'Show'} Jobs
                                {showJobs ? (
                                    <ChevronUp className="w-4 h-4" />
                                ) : (
                                    <ChevronDown className="w-4 h-4" />
                                )}
                            </Button>
                        </CollapsibleTrigger>
                    </Collapsible>
                </div>

                {scheduleInfo && (
                    <div className="text-sm text-muted-foreground">
                        <span className="capitalize">{scheduleInfo.sync_frequency}</span> sync
                        {scheduleInfo.next_scheduled_sync && (
                            <span className="ml-2">
                                • Next: {new Date(scheduleInfo.next_scheduled_sync).toLocaleTimeString()}
                            </span>
                        )}
                    </div>
                )}
            </div>

            {/* Job Status Messages */}
            {hasRunningJob && (
                <Alert>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <AlertDescription>
                        ETL job is running... This may take a few minutes.
                    </AlertDescription>
                </Alert>
            )}

            {!canTriggerJob && (
                <Alert variant="destructive">
                    <AlertDescription>
                        Connection must be in 'connected' state to run ETL jobs.
                    </AlertDescription>
                </Alert>
            )}

            {/* Jobs List */}
            <Collapsible open={showJobs} onOpenChange={setShowJobs}>
                <CollapsibleContent className="space-y-2">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">ETL Job History</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {jobsLoading ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="h-6 w-6 animate-spin" />
                                    <span className="ml-2 text-muted-foreground">Loading jobs...</span>
                                </div>
                            ) : jobs?.data?.length > 0 ? (
                                <div className="space-y-4">
                                    {jobs.data.slice(0, 10).map((job: any) => (
                                        <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                                            <div className="flex items-center space-x-3">
                                                {getJobStatusIcon(job.status)}
                                                <div>
                                                    <div className="font-medium text-sm">
                                                        {job.job_type.replace('_', ' ').toUpperCase()}
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">
                                                        Started: {job.started_at ? new Date(job.started_at).toLocaleString() : 'Not started'}
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="text-right space-y-1">
                                                <Badge variant={getJobStatusVariant(job.status)}>
                                                    {job.status}
                                                </Badge>
                                                {job.records_processed > 0 && (
                                                    <div className="text-xs text-muted-foreground">
                                                        {job.records_processed.toLocaleString()} records
                                                    </div>
                                                )}
                                                {job.error_message && (
                                                    <div className="text-xs text-red-600 max-w-xs truncate" title={job.error_message}>
                                                        Error: {job.error_message}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    No ETL jobs found. Click "Sync Data" to start your first job.
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </CollapsibleContent>
            </Collapsible>
        </div>
    );
};

export default ETLJobManager;