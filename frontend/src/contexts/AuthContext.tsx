import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { authService, type User } from '../services/api';
import { toast } from 'sonner';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (token) {
            checkAuthStatus();
        } else {
            setLoading(false);
        }
    }, []);

    const checkAuthStatus = async () => {
        try {
            const response = await authService.getCurrentUser();
            setUser(response.data);
        } catch (error) {
            localStorage.removeItem('access_token');
        } finally {
            setLoading(false);
        }
    };

    const login = async (username: string, password: string) => {
        try {
            const response = await authService.login(username, password);
            const { access_token } = response.data;

            localStorage.setItem('access_token', access_token);

            // Get user info
            const userResponse = await authService.getCurrentUser();
            setUser(userResponse.data);

            toast.success('Login successful!');
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Login failed');
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        setUser(null);
        toast.success('Logged out successfully');
    };

    const value = {
        user,
        loading,
        login,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
