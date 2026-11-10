import { apiFetch, setAuthToken } from './api';
import { AuthResponse, PlanType, User } from '../types';

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
    setAuthToken(null);
    return Promise.resolve();
  },

  getCurrentUser: async (token: string): Promise<User> => {
    return apiFetch<User>(`/auth/me?token=${token}`);
  },

  upgradePlan: async (plan: PlanType): Promise<User> => {
    return apiFetch<User>('/auth/plan', {
      method: 'POST',
      body: JSON.stringify({ plan }),
    });
  },
};
