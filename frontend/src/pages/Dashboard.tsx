import { useQuery } from '@tanstack/react-query';
import { connectionService, jobService } from '../services/api';
import { Link } from 'react-router-dom';
import { Database, Activity, CheckCircle, BarChart3, Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DatabaseConnection, ETLJob } from '@/types';

const Dashboard: React.FC = () => {
  const { data: connections, isLoading: connectionsLoading } = useQuery({
    queryKey: ['connections'],
    queryFn: () => connectionService.getConnections()
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['recent-jobs'],
    queryFn: () => jobService.getJobs()
  });

  const stats = [
    {
      title: "Total Connections",
      value: connections?.length || 0,
      icon: Database,
      color: "bg-gradient-accent"
    },
    {
      title: "Active Connections",
      value: connections?.filter((c: DatabaseConnection) => c.is_active && c.status === 'connected').length || 0,
      icon: CheckCircle,
      color: "bg-gradient-secondary"
    },
    {
      title: "Recent Jobs",
      value: jobs?.slice(0, 5).length || 0,
      icon: Activity,
      color: "bg-gradient-primary"
    }
  ];

  const recentConnections = connections?.slice(0, 5) || [];
  const recentJobs = jobs?.slice(0, 5) || [];

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'connected':
      case 'completed':
        return "bg-success/20 text-success border-success/30";
      case 'failed':
        return "bg-destructive/20 text-destructive border-destructive/30";
      case 'running':
      case 'testing':
        return "bg-warning/20 text-warning border-warning/30";
      default:
        return "bg-muted/20 text-muted-foreground border-muted/30";
    }
  };

  if (connectionsLoading || jobsLoading) {
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
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground">Monitor your database connections and analytics pipelines</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

        {/* Quick Actions */}
        <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
          <CardHeader>
            <CardTitle className="text-foreground">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <Button asChild className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated">
                <Link to="/connections">
                  <Database className="w-4 h-4 mr-2" />
                  Manage Connections
                </Link>
              </Button>
              <Button asChild variant="outline" className="border-border hover:bg-muted/50">
                <Link to="/analytics">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  View Analytics
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Connections */}
          <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
            <CardHeader>
              <CardTitle className="text-foreground">Recent Connections</CardTitle>
              <CardDescription>Your latest database connections</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {recentConnections.length > 0 ? (
                recentConnections.map((connection: DatabaseConnection) => (
                  <div key={connection.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/40">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-accent rounded-lg flex items-center justify-center">
                        <Database className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-medium text-foreground">{connection.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {connection.database_type} • Created {new Date(connection.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Badge className={getStatusBadgeClass(connection.status)}>
                      {connection.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-12">
                  <Database className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <h3 className="mt-2 text-sm font-medium text-foreground">No connections</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Get started by creating your first database connection.
                  </p>
                  <div className="mt-6">
                    <Button asChild className="bg-gradient-primary text-primary-foreground">
                      <Link to="/connections">
                        <Plus className="w-4 h-4 mr-2" />
                        Add Connection
                      </Link>
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Jobs */}
          <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
            <CardHeader>
              <CardTitle className="text-foreground">Recent Jobs</CardTitle>
              <CardDescription>Latest synchronization activities</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentJobs.length > 0 ? (
                recentJobs.map((job: ETLJob) => (
                  <div key={job.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/40">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${job.status === 'completed' ? 'bg-success' :
                        job.status === 'failed' ? 'bg-destructive' :
                          'bg-warning'
                        }`}></div>
                      <div>
                        <p className="font-medium text-sm text-foreground">{job.job_type}</p>
                        <p className="text-xs text-muted-foreground">
                          {job.records_processed} records • {new Date(job.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <Badge className={`${getStatusBadgeClass(job.status)} text-xs`}>
                      {job.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Activity className="mx-auto h-12 w-12 text-muted-foreground/50 mb-2" />
                  <p className="text-sm">No jobs found. ETL jobs will appear here once you start syncing data.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;