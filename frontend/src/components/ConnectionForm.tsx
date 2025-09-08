import React, { useState, useEffect } from 'react';
import { connectionService, type CreateConnectionRequest, type DatabaseConnection } from '../services/api';
import { useMutation } from '@tanstack/react-query';
import { EyeClosed, EyeIcon, X } from 'lucide-react';
import { toast } from 'sonner';
// import toast from 'react-hot-toast';
// import { XMarkIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

interface ConnectionFormProps {
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

const ConnectionForm: React.FC<ConnectionFormProps> = ({
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

    // Updated mutation usage for TanStack Query v5
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
            Promise.resolve(connectionService.updateConnection(id, data)),
        onSuccess: () => {
            toast.success('Connection updated successfully');
            onSuccess();
        },
        onError: (error: any) => {
            toast.error(error.response?.data?.detail || 'Failed to update connection');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
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

    const handleInputChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
    ) => {
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
            case 'postgresql':
                return 5432;
            case 'mysql':
                return 3306;
            case 'mongodb':
                return 27017;
            case 'oracle':
                return 1521;
            case 'mssql':
                return 1433;
            default:
                return 5432;
        }
    };

    const handleDatabaseTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const dbType = e.target.value;
        setFormData(prev => ({
            ...prev,
            database_type: dbType,
            credentials: {
                ...prev.credentials,
                port: getDefaultPort(dbType),
            },
        }));
    };

    const isLoading = createMutation.isPending || updateMutation.isPending;

    if (isLoading) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
                <div className="flex items-center justify-between p-6 border-b">
                    <h3 className="text-lg font-medium text-gray-900">
                        {isEditing ? 'Edit Connection' : 'Add New Connection'}
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-500"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Connection Name */}
                    <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                            Connection Name *
                        </label>
                        <input
                            type="text"
                            id="name"
                            name="name"
                            required
                            value={formData.name}
                            onChange={handleInputChange}
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="My Database Connection"
                        />
                    </div>

                    {/* Database Type */}
                    <div>
                        <label htmlFor="database_type" className="block text-sm font-medium text-gray-700">
                            Database Type *
                        </label>
                        <select
                            id="database_type"
                            name="database_type"
                            required
                            value={formData.database_type}
                            onChange={handleDatabaseTypeChange}
                            disabled={isEditing}
                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                        >
                            {DATABASE_TYPES.map((type) => (
                                <option key={type.value} value={type.value}>
                                    {type.label}
                                </option>
                            ))}
                        </select>
                        {isEditing && (
                            <p className="mt-1 text-sm text-gray-500">
                                Database type cannot be changed for existing connections
                            </p>
                        )}
                    </div>

                    {/* Connection Details */}
                    {!isEditing && (
                        <>
                            <div className="border-t pt-6">
                                <h4 className="text-md font-medium text-gray-900 mb-4">Connection Details</h4>

                                <div className="grid grid-cols-2 gap-4">
                                    {/* Host */}
                                    <div>
                                        <label htmlFor="credentials.host" className="block text-sm font-medium text-gray-700">
                                            Host *
                                        </label>
                                        <input
                                            type="text"
                                            id="credentials.host"
                                            name="credentials.host"
                                            required
                                            value={formData.credentials.host}
                                            onChange={handleInputChange}
                                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            placeholder="localhost"
                                        />
                                    </div>

                                    {/* Port */}
                                    <div>
                                        <label htmlFor="credentials.port" className="block text-sm font-medium text-gray-700">
                                            Port *
                                        </label>
                                        <input
                                            type="number"
                                            id="credentials.port"
                                            name="credentials.port"
                                            required
                                            value={formData.credentials.port}
                                            onChange={handleInputChange}
                                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4 mt-4">
                                    {/* Username */}
                                    <div>
                                        <label htmlFor="credentials.username" className="block text-sm font-medium text-gray-700">
                                            Username *
                                        </label>
                                        <input
                                            type="text"
                                            id="credentials.username"
                                            name="credentials.username"
                                            required
                                            value={formData.credentials.username}
                                            onChange={handleInputChange}
                                            className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            autoComplete="username"
                                        />
                                    </div>

                                    {/* Password */}
                                    <div>
                                        <label htmlFor="credentials.password" className="block text-sm font-medium text-gray-700">
                                            Password *
                                        </label>
                                        <div className="relative mt-1">
                                            <input
                                                type={showPassword ? 'text' : 'password'}
                                                id="credentials.password"
                                                name="credentials.password"
                                                required
                                                value={formData.credentials.password}
                                                onChange={handleInputChange}
                                                className="block w-full border border-gray-300 rounded-md px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                                autoComplete="current-password"
                                            />
                                            <button
                                                type="button"
                                                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                                                onClick={() => setShowPassword(!showPassword)}
                                            >
                                                {showPassword ? (
                                                    <EyeClosed className="h-4 w-4 text-gray-400" />
                                                ) : (
                                                    <EyeIcon className="h-4 w-4 text-gray-400" />
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Database Name */}
                                <div className="mt-4">
                                    <label htmlFor="credentials.database_name" className="block text-sm font-medium text-gray-700">
                                        Database Name *
                                    </label>
                                    <input
                                        type="text"
                                        id="credentials.database_name"
                                        name="credentials.database_name"
                                        required
                                        value={formData.credentials.database_name}
                                        onChange={handleInputChange}
                                        className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="my_database"
                                    />
                                </div>

                                {/* MongoDB specific fields */}
                                {formData.database_type === 'mongodb' && (
                                    <div className="mt-4">
                                        <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded-md">
                                            <strong>MongoDB Connection:</strong> You can also provide a connection string in the host field
                                            (e.g., mongodb://username:password@host:port/database) and leave other fields empty.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* Sync Settings */}
                    <div className="border-t pt-6">
                        <h4 className="text-md font-medium text-gray-900 mb-4">Sync Settings</h4>

                        <div>
                            <label htmlFor="sync_frequency" className="block text-sm font-medium text-gray-700">
                                Sync Frequency
                            </label>
                            <select
                                id="sync_frequency"
                                name="sync_frequency"
                                value={formData.sync_frequency}
                                onChange={handleInputChange}
                                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                                {SYNC_FREQUENCIES.map((freq) => (
                                    <option key={freq.value} value={freq.value}>
                                        {freq.label}
                                    </option>
                                ))}
                            </select>
                            <p className="mt-1 text-sm text-gray-500">
                                How often should we sync data from this database?
                            </p>
                        </div>
                    </div>

                    {/* Form Actions */}
                    <div className="flex justify-end space-x-3 pt-6 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <div className="flex items-center">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    {isEditing ? 'Updating...' : 'Creating...'}
                                </div>
                            ) : (
                                isEditing ? 'Update Connection' : 'Create Connection'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ConnectionForm;