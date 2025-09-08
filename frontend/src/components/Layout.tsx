import React, { type ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight, ChartBarIcon, Cog, Database, Gpu, HomeIcon } from 'lucide-react';

interface LayoutProps {
    children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const { user, logout } = useAuth();
    const location = useLocation();

    const navigation = [
        { name: 'Dashboard', href: '/', icon: HomeIcon },
        { name: 'Connections', href: '/connections', icon: Database },
        { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
        { name: 'ETL Dashboard', href: '/etl', icon: Gpu },
        { name: 'Settings', href: '/settings', icon: Cog },
    ];

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Sidebar */}
            <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg">
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="flex items-center px-6 py-4 border-b">
                        <h1 className="text-xl font-bold text-gray-900">Analytics Connector</h1>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 px-4 py-4 space-y-2">
                        {navigation.map((item) => {
                            const isActive = location.pathname === item.href;
                            return (
                                <Link
                                    key={item.name}
                                    to={item.href}
                                    className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${isActive
                                        ? 'bg-blue-100 text-blue-700'
                                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                                        }`}
                                >
                                    <item.icon className="w-5 h-5 mr-3" />
                                    {item.name}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* User info and logout */}
                    <div className="p-4 border-t">
                        <div className="flex items-center mb-4">
                            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                                <span className="text-sm font-medium text-white">
                                    {user?.username?.charAt(0).toUpperCase()}
                                </span>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm font-medium text-gray-900">{user?.username}</p>
                                <p className="text-xs text-gray-500">{user?.email}</p>
                            </div>
                        </div>
                        <button
                            onClick={logout}
                            className="flex items-center w-full px-4 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-100 hover:text-gray-900"
                        >
                            <ArrowRight className="w-5 h-5 mr-3" />
                            Logout
                        </button>
                    </div>
                </div>
            </div>

            {/* Main content */}
            <div className="pl-64">
                <main className="p-8">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;