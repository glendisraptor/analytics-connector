import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Connections from './pages/Connections';
import Analytics from './pages/Analytics';
import Layout from './components/Layout';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from "@/components/ui/sonner"
import ETLDashboard from './components/ETLDashboard';
import Settings from './pages/Settings';

const queryClient = new QueryClient();

// Protected Route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { user, loading } = useAuth();

    if (loading) {
        return <div className="flex items-center justify-center min-h-screen">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
        </div>;
    }

    return user ? <Layout>{children}</Layout> : <Navigate to="/login" />;
};

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <Router>
                    <div className="App">
                        <Routes>
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />
                            <Route path="/" element={
                                <ProtectedRoute>
                                    <Dashboard />
                                </ProtectedRoute>
                            } />
                            <Route path="/connections" element={
                                <ProtectedRoute>
                                    <Connections />
                                </ProtectedRoute>
                            } />
                            <Route path="/analytics" element={
                                <ProtectedRoute>
                                    <Analytics />
                                </ProtectedRoute>
                            } />
                            <Route path="/etl" element={
                                <ProtectedRoute>
                                    <ETLDashboard />
                                </ProtectedRoute>
                            } />

                            <Route path="/settings" element={
                                <ProtectedRoute>
                                    <Settings />
                                </ProtectedRoute>
                            } />
                            {/* 404 */}

                        </Routes>
                        <Toaster position="top-right" />
                    </div>
                </Router>
            </AuthProvider>
        </QueryClientProvider>
    );
}

export default App;