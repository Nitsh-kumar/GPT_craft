import { apiFetch, setAuthToken } from './api';
import { AuthResponse, User } from '../types';

export const authService = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    // Simulated API call
    // return apiFetch<AuthResponse>('/api/auth/login', {
    //   method: 'POST',
    //   body: JSON.stringify({ email, password }),
    // });
    
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        const token = 'mock-jwt-token-123';
        setAuthToken(token);
        resolve({
          accessToken: token,
          user: { id: '1', email, name: 'Test User', plan: 'free' },
        });
      }, 1000);
    });
  },

  register: async (name: string, email: string, password: string): Promise<AuthResponse> => {
    // return apiFetch<AuthResponse>('/api/auth/register', {
    //   method: 'POST',
    //   body: JSON.stringify({ name, email, password }),
    // });
    
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        const token = 'mock-jwt-token-123';
        setAuthToken(token);
        resolve({
          accessToken: token,
          user: { id: '1', email, name, plan: 'free' },
        });
      }, 1000);
    });
  },

  logout: async (): Promise<void> => {
    // return apiFetch<void>('/api/auth/logout', { method: 'POST' });
    setAuthToken(null);
    return Promise.resolve();
  },

  getCurrentUser: async (): Promise<User> => {
    // return apiFetch<User>('/api/auth/me');
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ id: '1', email: 'test@example.com', name: 'Test User', plan: 'free' });
      }, 500);
    });
  },
};
