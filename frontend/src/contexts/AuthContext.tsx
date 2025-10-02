/* eslint-disable @typescript-eslint/no-explicit-any */
import React, {
    createContext,
    useState,
    useEffect,
    type ReactNode,
} from "react";
import { authService } from "../services/api";
import { toast } from "sonner";
import type { User } from "@/types";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (token) {
            checkAuthStatus();
        } else {
            setLoading(false);
        }
    }, []);

    const checkAuthStatus = async () => {
        try {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
        } catch (error) {
            console.error("Auth check failed:", error);
            localStorage.removeItem("access_token");
        } finally {
            setLoading(false);
        }
    };

    const login = async (username: string, password: string) => {
        try {
            const loginResponse = await authService.login(username, password);
            const { access_token } = loginResponse;

            localStorage.setItem("access_token", access_token);

            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);

            toast.success("Login successful!");
        } catch (error: any) {
            toast.error(error?.message || "Login failed");
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
        toast.success("Logged out successfully");
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};
