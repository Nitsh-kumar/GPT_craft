import { apiFetch, setAuthToken } from './api';
import { AuthResponse, User } from '../types';

export const authService = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    return apiFetch<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  register: async (name: string, email: string, password: string): Promise<AuthResponse> => {
    return apiFetch<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
  },

  logout: async (): Promise<void> => {
    // return apiFetch<void>('/api/auth/logout', { method: 'POST' });
    setAuthToken(null);
    return Promise.resolve();
  },

  getCurrentUser: async (token: string): Promise<User> => {
    return apiFetch<User>(`/auth/me?token=${token}`);
  },
};
