/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    User,
    Settings as SettingsIcon,
    Clock,
    Shield,
    Bell,
    Database,
    BarChart3,
    Loader2,
    Save
} from 'lucide-react';
import { settingsService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

const Settings: React.FC = () => {

    const tabs = [
        { id: 'profile', name: 'Profile', icon: User },
        { id: 'connections', name: 'Connections', icon: Database },
        { id: 'scheduling', name: 'Scheduling', icon: Clock },
        { id: 'analytics', name: 'Analytics', icon: BarChart3 },
        { id: 'notifications', name: 'Notifications', icon: Bell },
        { id: 'security', name: 'Security', icon: Shield },
        { id: 'system', name: 'System', icon: SettingsIcon },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground">
                    Manage your account, connections, and system preferences
                </p>
            </div>

            {/* Settings Navigation */}
            <Tabs defaultValue="profile" className="space-y-4">
                <TabsList className="grid w-full grid-cols-4 lg:grid-cols-7">
                    {tabs.map((tab) => (
                        <TabsTrigger key={tab.id} value={tab.id} className="flex items-center gap-2">
                            <tab.icon className="w-4 h-4" />
                            <span className="hidden sm:inline">{tab.name}</span>
                        </TabsTrigger>
                    ))}
                </TabsList>

                <TabsContent value="profile">
                    <ProfileSettings />
                </TabsContent>

                <TabsContent value="connections">
                    <ConnectionSettings />
                </TabsContent>

                <TabsContent value="scheduling">
                    <SchedulingSettings />
                </TabsContent>

                <TabsContent value="analytics">
                    <AnalyticsSettings />
                </TabsContent>

                <TabsContent value="notifications">
                    <NotificationSettings />
                </TabsContent>

                <TabsContent value="security">
                    <SecuritySettings />
                </TabsContent>

                <TabsContent value="system">
                    <SystemSettings />
                </TabsContent>
            </Tabs>
        </div>
    );
};

// Profile Settings Component
const ProfileSettings: React.FC = () => {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [formData, setFormData] = useState({
        full_name: user?.full_name || '',
        email: user?.email || '',
        username: user?.username || '',
    });

    const updateProfileMutation = useMutation({
        mutationFn: async (data: any) => settingsService.updateProfile(data),
        onSuccess: () => {
            toast.success('Profile updated successfully');
            queryClient.invalidateQueries({ queryKey: ['user'] });
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to update profile');
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateProfileMutation.mutate(formData);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>
                    Update your personal information and account details.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="full_name">Full Name</Label>
                            <Input
                                id="full_name"
                                value={formData.full_name}
                                onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="email">Email Address</Label>
                            <Input
                                id="email"
                                type="email"
                                value={formData.email}
                                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                value={formData.username}
                                onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                            />
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button
                            type="submit"
                            disabled={updateProfileMutation.isPending}
                            className="gap-2"
                        >
                            {updateProfileMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Save className="w-4 h-4" />
                            )}
                            {updateProfileMutation.isPending ? 'Updating...' : 'Update Profile'}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
};

// Connection Settings Component
const ConnectionSettings: React.FC = () => {
    const queryClient = useQueryClient();

    const { data: settings, isLoading } = useQuery({
        queryKey: ['connection-settings'],
        queryFn: () => settingsService.getConnectionSettings()
    });

    const updateSettingsMutation = useMutation({
        mutationFn: async (data: any) => settingsService.updateConnectionSettings(data),
        onSuccess: () => {
            toast.success('Connection settings updated');
            queryClient.invalidateQueries({ queryKey: ['connection-settings'] });
        },
        onError: (error: any) => {
            console.error("Error updating settings:", error);
            toast.error('Failed to update settings');
        }
    });

    const [formData, setFormData] = useState({
        auto_sync_to_superset: true,
        default_sync_frequency: 'daily',
        connection_timeout: 30,
        max_retry_attempts: 3,
        encrypt_credentials: true,
    });

    React.useEffect(() => {
        if (settings?.data) {
            setFormData(settings.data);
        }
    }, [settings]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateSettingsMutation.mutate(formData);
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading settings...</span>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Connection Preferences</CardTitle>
                <CardDescription>
                    Configure default settings for database connections.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base">Auto-sync to Superset</Label>
                                <p className="text-sm text-muted-foreground">
                                    Automatically add new connections to Superset for analytics
                                </p>
                            </div>
                            <Switch
                                checked={formData.auto_sync_to_superset}
                                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, auto_sync_to_superset: checked }))}
                            />
                        </div>

                        <Separator />

                        <div className="space-y-2">
                            <Label htmlFor="default_sync_frequency">Default Sync Frequency</Label>
                            <Select
                                value={formData.default_sync_frequency}
                                onValueChange={(value) => setFormData(prev => ({ ...prev, default_sync_frequency: value }))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select frequency" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="hourly">Hourly</SelectItem>
                                    <SelectItem value="daily">Daily</SelectItem>
                                    <SelectItem value="weekly">Weekly</SelectItem>
                                    <SelectItem value="monthly">Monthly</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="connection_timeout">Connection Timeout (seconds)</Label>
                                <Input
                                    id="connection_timeout"
                                    type="number"
                                    min="10"
                                    max="300"
                                    value={formData.connection_timeout}
                                    onChange={(e) => setFormData(prev => ({ ...prev, connection_timeout: parseInt(e.target.value) }))}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="max_retry_attempts">Max Retry Attempts</Label>
                                <Input
                                    id="max_retry_attempts"
                                    type="number"
                                    min="1"
                                    max="10"
                                    value={formData.max_retry_attempts}
                                    onChange={(e) => setFormData(prev => ({ ...prev, max_retry_attempts: parseInt(e.target.value) }))}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button
                            type="submit"
                            disabled={updateSettingsMutation.isPending}
                            className="gap-2"
                        >
                            {updateSettingsMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Save className="w-4 h-4" />
                            )}
                            {updateSettingsMutation.isPending ? 'Updating...' : 'Update Settings'}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
};

// Scheduling Settings Component
const SchedulingSettings: React.FC = () => {
    const { data: schedules, isLoading } = useQuery({
        queryKey: ['etl-schedules'],
        queryFn: () => settingsService.getETLSchedules()
    });

    const updateScheduleMutation = useMutation({
        mutationFn: async ({ connectionId, schedule }: { connectionId: number; schedule: any }) =>
            settingsService.updateETLSchedule(connectionId, schedule),
        onSuccess: () => {
            toast.success('Schedule updated successfully');
        },
        onError: () => {
            toast.error('Failed to update schedule');
        }
    });

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading schedules...</span>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>ETL Scheduling</CardTitle>
                <CardDescription>
                    Manage automatic data synchronization schedules for your connections.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {schedules?.data?.map((schedule: any) => (
                        <ScheduleCard
                            key={schedule.connection_id}
                            schedule={schedule}
                            onUpdate={(newSchedule) =>
                                updateScheduleMutation.mutate({
                                    connectionId: schedule.connection_id,
                                    schedule: newSchedule
                                })
                            }
                        />
                    ))}

                    {(!schedules?.data || schedules.data.length === 0) && (
                        <div className="text-center py-8 text-muted-foreground">
                            No database connections found. Create connections to manage their schedules.
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};

// Schedule Card Component
interface ScheduleCardProps {
    schedule: any;
    onUpdate: (schedule: any) => void;
}

const ScheduleCard: React.FC<ScheduleCardProps> = ({ schedule, onUpdate }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({
        frequency: schedule.sync_frequency,
        enabled: schedule.is_active,
        time: schedule.scheduled_time || '02:00',
    });

    const handleSave = () => {
        onUpdate(formData);
        setIsEditing(false);
    };

    return (
        <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between">
                <div>
                    <h4 className="font-medium">{schedule.connection_name}</h4>
                    <p className="text-sm text-muted-foreground capitalize">
                        {schedule.database_type} • {schedule.sync_frequency} sync
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    {!isEditing ? (
                        <>
                            <Badge variant={schedule.is_active ? "default" : "secondary"}>
                                {schedule.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsEditing(true)}
                            >
                                Edit
                            </Button>
                        </>
                    ) : (
                        <div className="flex items-center gap-2">
                            <Select
                                value={formData.frequency}
                                onValueChange={(value) => setFormData(prev => ({ ...prev, frequency: value }))}
                            >
                                <SelectTrigger className="w-32">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="hourly">Hourly</SelectItem>
                                    <SelectItem value="daily">Daily</SelectItem>
                                    <SelectItem value="weekly">Weekly</SelectItem>
                                    <SelectItem value="monthly">Monthly</SelectItem>
                                </SelectContent>
                            </Select>

                            <Input
                                type="time"
                                value={formData.time}
                                onChange={(e) => setFormData(prev => ({ ...prev, time: e.target.value }))}
                                className="w-32"
                            />

                            <Switch
                                checked={formData.enabled}
                                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, enabled: checked }))}
                            />

                            <Button size="sm" onClick={handleSave}>
                                Save
                            </Button>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsEditing(false)}
                            >
                                Cancel
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// Analytics Settings Component
const AnalyticsSettings: React.FC = () => {
    const [settings, setSettings] = useState({
        superset_auto_create_datasets: true,
        superset_auto_create_dashboards: false,
        data_retention_days: 365,
        enable_data_profiling: true,
    });

    const updateSettingsMutation = useMutation({
        mutationFn: async (data: any) => settingsService.updateAnalyticsSettings(data),
        onSuccess: () => {
            toast.success('Analytics settings updated');
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        updateSettingsMutation.mutate(settings);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Analytics Configuration</CardTitle>
                <CardDescription>
                    Configure how your data appears in analytics platforms.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base">Auto-create Datasets in Superset</Label>
                                <p className="text-sm text-muted-foreground">
                                    Automatically create datasets when new data is synced
                                </p>
                            </div>
                            <Switch
                                checked={settings.superset_auto_create_datasets}
                                onCheckedChange={(checked) => setSettings(prev => ({ ...prev, superset_auto_create_datasets: checked }))}
                            />
                        </div>

                        <Separator />

                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label className="text-base">Auto-create Basic Dashboards</Label>
                                <p className="text-sm text-muted-foreground">
                                    Create overview dashboards for new connections
                                </p>
                            </div>
                            <Switch
                                checked={settings.superset_auto_create_dashboards}
                                onCheckedChange={(checked) => setSettings(prev => ({ ...prev, superset_auto_create_dashboards: checked }))}
                            />
                        </div>

                        <Separator />

                        <div className="space-y-2">
                            <Label htmlFor="data_retention_days">Data Retention (days)</Label>
                            <Input
                                id="data_retention_days"
                                type="number"
                                min="30"
                                max="3650"
                                value={settings.data_retention_days}
                                onChange={(e) => setSettings(prev => ({ ...prev, data_retention_days: parseInt(e.target.value) }))}
                            />
                            <p className="text-sm text-muted-foreground">
                                How long to keep historical data in analytics database
                            </p>
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button
                            type="submit"
                            disabled={updateSettingsMutation.isPending}
                            className="gap-2"
                        >
                            {updateSettingsMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Save className="w-4 h-4" />
                            )}
                            {updateSettingsMutation.isPending ? 'Updating...' : 'Update Settings'}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
};

// Notification Settings Component
const NotificationSettings: React.FC = () => {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Coming soon...</CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Notification settings will be available in a future update.
                </p>
            </CardContent>
        </Card>
    );
};

// Security Settings Component  
const SecuritySettings: React.FC = () => {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Security Settings</CardTitle>
                <CardDescription>Coming soon...</CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Security settings will be available in a future update.
                </p>
            </CardContent>
        </Card>
    );
};

// System Settings Component
const SystemSettings: React.FC = () => {
    const { data: systemInfo, isLoading } = useQuery({
        queryKey: ['system-info'],
        queryFn: () => settingsService.getSystemInfo()
    });

    return (
        <Card>
            <CardHeader>
                <CardTitle>System Information</CardTitle>
                <CardDescription>
                    View system status and configuration details.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin" />
                        <span className="ml-2">Loading system info...</span>
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium text-muted-foreground">Application Version</Label>
                            <p className="text-sm">{systemInfo?.app_version || 'N/A'}</p>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium text-muted-foreground">Database Status</Label>
                            <p className="text-sm">{systemInfo?.database_status || 'N/A'}</p>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium text-muted-foreground">Superset Status</Label>
                            <p className="text-sm">{systemInfo?.superset_status || 'N/A'}</p>
                        </div>
                        <div className="space-y-2">
                            <Label className="text-sm font-medium text-muted-foreground">Total Connections</Label>
                            <p className="text-sm">{systemInfo?.total_connections || 0}</p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default Settings;