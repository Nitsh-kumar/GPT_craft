import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { PlanType, User } from '../types';
import { authService } from '../services/authService';
import { setAuthToken } from '../services/api';
import { supabase } from '../lib/supabase';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
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
      try {
        // 1. Check active Supabase session
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          localStorage.setItem('accessToken', session.access_token);
          setAuthToken(session.access_token);
          const currentUser = await authService.getCurrentUser(session.access_token);
          setUser(currentUser);
          setIsLoading(false);
          return;
        }

        // 2. Fallback to stored token (e.g. from redirect or local storage)
        const storedToken = localStorage.getItem('accessToken');
        if (storedToken) {
          setAuthToken(storedToken);
          const currentUser = await authService.getCurrentUser(storedToken);
          setUser(currentUser);
        }
      } catch (error) {
        console.error('Failed to restore session', error);
        localStorage.removeItem('accessToken');
        setAuthToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();

    // Listen to Supabase auth state changes (sign in, sign out, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session?.access_token) {
        localStorage.setItem('accessToken', session.access_token);
        setAuthToken(session.access_token);
        if (event === 'SIGNED_IN') {
          try {
            const currentUser = await authService.getCurrentUser(session.access_token);
            setUser(currentUser);
          } catch (err) {
            console.error('Error fetching user profile after sign-in:', err);
          }
        }
      } else if (event === 'SIGNED_OUT') {
        localStorage.removeItem('accessToken');
        setAuthToken(null);
        setUser(null);
      }
    });

    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      // Authenticate via Supabase Auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw new Error(error.message);
      }

      if (!data.session?.access_token) {
        throw new Error('Authentication succeeded but no access token was returned.');
      }

      const token = data.session.access_token;
      localStorage.setItem('accessToken', token);
      setAuthToken(token);

      // Sync and retrieve user profile from backend
      const currentUser = await authService.getCurrentUser(token);
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithToken = useCallback(async (token: string) => {
    setIsLoading(true);
    try {
      localStorage.setItem('accessToken', token);
      setAuthToken(token);
      const currentUser = await authService.getCurrentUser(token);
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth-success`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
        skipBrowserRedirect: true,
      },
    });

    if (error) {
      throw new Error(error.message);
    }

    if (!data?.url) {
      throw new Error('Failed to generate Google authentication link.');
    }

    // Pre-flight check the authorize URL to intercept unconfigured Supabase provider errors
    try {
      const response = await fetch(data.url, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        redirect: 'manual',
      });

      if (response.status === 400 || response.status === 422) {
        const body = await response.json().catch(() => null);
        const detail = body?.msg || body?.message || 'provider is not enabled';
        throw new Error(
          `Google Sign-In is not enabled on this Supabase project (${detail}). Please enable Google in Supabase Dashboard -> Authentication -> Providers.`
        );
      }
    } catch (fetchErr: any) {
      if (fetchErr.message && fetchErr.message.includes('Google Sign-In is not enabled')) {
        throw fetchErr;
      }
      // Opaque redirect (status 0/302) occurs when provider is active and redirecting to Google
    }

    window.location.assign(data.url);
  };

  const register = async (name: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { name },
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      if (data.user && (!data.user.identities || data.user.identities.length === 0)) {
        throw new Error('Email already registered. Please sign in instead.');
      }

      // If email is auto-confirmed or session is active immediately
      let token = data.session?.access_token;
      if (!token) {
        // Attempt immediate login if auto-confirmed by database trigger
        const loginRes = await supabase.auth.signInWithPassword({ email, password });
        token = loginRes.data.session?.access_token;
      }

      if (token) {
        localStorage.setItem('accessToken', token);
        setAuthToken(token);
        const currentUser = await authService.getCurrentUser(token);
        setUser(currentUser);
      }
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
    supabase.auth.signOut().catch(() => {});
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
        loginWithGoogle,
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
