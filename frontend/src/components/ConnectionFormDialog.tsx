import { useState, useEffect, type FormEvent, type ChangeEvent } from 'react';
import { connectionService, type CreateConnectionRequest, type DatabaseConnection } from '../services/api';
import { useMutation } from '@tanstack/react-query';
import { Eye, EyeOff, X, Database } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ConnectionFormDialogProps {
    connection?: DatabaseConnection | null;
    onClose: () => void;
    onSuccess: () => void;
}

const DATABASE_TYPES = [
    { value: 'postgresql', label: 'PostgreSQL' },
    { value: 'mysql', label: 'MySQL' },
    { value: 'mongodb', label: 'MongoDB' },
    { value: 'sqlite', label: 'SQLite' },
    { value: 'oracle', label: 'Oracle' },
    { value: 'mssql', label: 'SQL Server' },
];

const SYNC_FREQUENCIES = [
    { value: 'hourly', label: 'Hourly' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
];

const ConnectionFormDialog: React.FC<ConnectionFormDialogProps> = ({
    connection,
    onClose,
    onSuccess,
}) => {
    const [showPassword, setShowPassword] = useState(false);
    const [formData, setFormData] = useState<CreateConnectionRequest>({
        name: '',
        database_type: 'postgresql',
        credentials: {
            host: '',
            port: 5432,
            username: '',
            password: '',
            database_name: '',
            additional_params: {},
        },
        sync_frequency: 'daily',
    });

    const isEditing = !!connection;

    useEffect(() => {
        if (connection) {
            setFormData({
                name: connection.name,
                database_type: connection.database_type,
                credentials: {
                    host: '',
                    port: 5432,
                    username: '',
                    password: '',
                    database_name: '',
                    additional_params: {},
                },
                sync_frequency: connection.sync_frequency,
            });
        }
    }, [connection]);

    const createMutation = useMutation({
        mutationFn: (data: CreateConnectionRequest) => connectionService.createConnection(data),
        onSuccess: () => {
            toast.success('Connection created successfully');
            onSuccess();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to create connection');
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: number; data: Partial<DatabaseConnection> }) =>
            connectionService.updateConnection(id, data),
        onSuccess: () => {
            toast.success('Connection updated successfully');
            onSuccess();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to update connection');
        },
    });

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        if (isEditing && connection) {
            updateMutation.mutate({
                id: connection.id,
                data: {
                    name: formData.name,
                    sync_frequency: formData.sync_frequency,
                },
            });
        } else {
            createMutation.mutate(formData);
        }
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;

        if (name.startsWith('credentials.')) {
            const credentialField = name.split('.')[1];
            setFormData(prev => ({
                ...prev,
                credentials: {
                    ...prev.credentials,
                    [credentialField]: credentialField === 'port' ? parseInt(value) || 0 : value,
                },
            }));
        } else {
            setFormData(prev => ({
                ...prev,
                [name]: value,
            }));
        }
    };

    const getDefaultPort = (dbType: string) => {
        switch (dbType) {
            case 'postgresql': return 5432;
            case 'mysql': return 3306;
            case 'mongodb': return 27017;
            case 'oracle': return 1521;
            case 'mssql': return 1433;
            default: return 5432;
        }
    };

    const handleDatabaseTypeChange = (value: string) => {
        setFormData(prev => ({
            ...prev,
            database_type: value,
            credentials: {
                ...prev.credentials,
                port: getDefaultPort(value),
            },
        }));
    };

    const isLoading = createMutation.isPending || updateMutation.isPending;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <CardHeader className="border-b border-border/40">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-primary rounded-lg flex items-center justify-center">
                                <Database className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <CardTitle className="text-xl">
                                    {isEditing ? 'Edit Connection' : 'Add New Connection'}
                                </CardTitle>
                                <CardDescription>
                                    {isEditing ? 'Update connection settings' : 'Connect to your database'}
                                </CardDescription>
                            </div>
                        </div>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={onClose}
                            className="text-muted-foreground hover:text-foreground"
                        >
                            <X className="w-5 h-5" />
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="pt-6">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* Connection Name */}
                        <div className="space-y-2">
                            <Label htmlFor="name">Connection Name *</Label>
                            <Input
                                id="name"
                                name="name"
                                required
                                value={formData.name}
                                onChange={handleInputChange}
                                placeholder="My Database Connection"
                            />
                        </div>

                        {/* Database Type */}
                        <div className="space-y-2">
                            <Label htmlFor="database_type">Database Type *</Label>
                            <Select
                                value={formData.database_type}
                                onValueChange={handleDatabaseTypeChange}
                                disabled={isEditing}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {DATABASE_TYPES.map((type) => (
                                        <SelectItem key={type.value} value={type.value}>
                                            {type.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {isEditing && (
                                <p className="text-sm text-muted-foreground">
                                    Database type cannot be changed for existing connections
                                </p>
                            )}
                        </div>

                        {/* Connection Details */}
                        {!isEditing && (
                            <div className="space-y-4 p-4 bg-muted/30 rounded-lg border border-border/40">
                                <h4 className="font-medium text-foreground">Connection Details</h4>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="credentials.host">Host *</Label>
                                        <Input
                                            id="credentials.host"
                                            name="credentials.host"
                                            required
                                            value={formData.credentials.host}
                                            onChange={handleInputChange}
                                            placeholder="localhost"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="credentials.port">Port *</Label>
                                        <Input
                                            type="number"
                                            id="credentials.port"
                                            name="credentials.port"
                                            required
                                            value={formData.credentials.port}
                                            onChange={handleInputChange}
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="credentials.username">Username *</Label>
                                        <Input
                                            id="credentials.username"
                                            name="credentials.username"
                                            required
                                            value={formData.credentials.username}
                                            onChange={handleInputChange}
                                            autoComplete="username"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="credentials.password">Password *</Label>
                                        <div className="relative">
                                            <Input
                                                type={showPassword ? 'text' : 'password'}
                                                id="credentials.password"
                                                name="credentials.password"
                                                required
                                                value={formData.credentials.password}
                                                onChange={handleInputChange}
                                                autoComplete="current-password"
                                            />
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                                                onClick={() => setShowPassword(!showPassword)}
                                            >
                                                {showPassword ? (
                                                    <EyeOff className="h-4 w-4" />
                                                ) : (
                                                    <Eye className="h-4 w-4" />
                                                )}
                                            </Button>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="credentials.database_name">Database Name *</Label>
                                    <Input
                                        id="credentials.database_name"
                                        name="credentials.database_name"
                                        required
                                        value={formData.credentials.database_name}
                                        onChange={handleInputChange}
                                        placeholder="my_database"
                                    />
                                </div>

                                {formData.database_type === 'mongodb' && (
                                    <div className="bg-info/10 p-3 rounded-md border border-info/20">
                                        <p className="text-sm text-foreground">
                                            <strong>MongoDB Connection:</strong> You can also provide a connection string in the host field
                                            (e.g., mongodb://username:password@host:port/database) and leave other fields empty.
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Sync Settings */}
                        <div className="space-y-4 p-4 bg-muted/30 rounded-lg border border-border/40">
                            <h4 className="font-medium text-foreground">Sync Settings</h4>

                            <div className="space-y-2">
                                <Label htmlFor="sync_frequency">Sync Frequency</Label>
                                <Select
                                    value={formData.sync_frequency}
                                    onValueChange={(value) => setFormData(prev => ({ ...prev, sync_frequency: value }))}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {SYNC_FREQUENCIES.map((freq) => (
                                            <SelectItem key={freq.value} value={freq.value}>
                                                {freq.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <p className="text-sm text-muted-foreground">
                                    How often should we sync data from this database?
                                </p>
                            </div>
                        </div>

                        {/* Form Actions */}
                        <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={onClose}
                                className="border-border hover:bg-muted/50"
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={isLoading}
                                className="bg-gradient-primary text-primary-foreground hover:opacity-90"
                            >
                                {isLoading ? (
                                    <>Processing...</>
                                ) : (
                                    isEditing ? 'Update Connection' : 'Create Connection'
                                )}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};

export default ConnectionFormDialog;