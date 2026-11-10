import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { PlanType, User } from '../types';
import { authService } from '../services/authService';
import { setAuthToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  upgradePlan: (plan: PlanType) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('accessToken');
      if (storedToken) {
        try {
          setAuthToken(storedToken);
          const currentUser = await authService.getCurrentUser(storedToken);
          setUser(currentUser);
        } catch (error) {
          console.error('Failed to restore session', error);
          localStorage.removeItem('accessToken');
          setAuthToken(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();

    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authService.login(email, password);
      localStorage.setItem('accessToken', response.accessToken);
      setAuthToken(response.accessToken);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithToken = async (token: string) => {
    setIsLoading(true);
    try {
      const currentUser = await authService.getCurrentUser(token);
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authService.register(name, email, password);
      localStorage.setItem('accessToken', response.accessToken);
      setAuthToken(response.accessToken);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  };

  const upgradePlan = async (plan: PlanType) => {
    const updatedUser = await authService.upgradePlan(plan);
    setUser(updatedUser);
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    setAuthToken(null);
    setUser(null);
    authService.logout();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        loginWithToken,
        register,
        upgradePlan,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
