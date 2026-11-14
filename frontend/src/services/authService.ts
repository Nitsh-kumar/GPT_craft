import { apiFetch, setAuthToken } from './api';
import { AuthResponse, PlanType, User } from '../types';

const AUTH_ERROR_MESSAGES: Record<string, string> = {
  auth_failed: 'Authentication failed. Please try again.',
  account_inactive: 'This account is inactive. Please contact support.',
  failed_to_get_user_info: 'Failed to get user information from Google.',
  invalid_user_data_from_google: 'Google did not provide essential account information.',
  session_creation_failed: "Login successful, but we couldn't start your session.",
};

export function formatAuthErrorMessage(errorParam: string): string {
  return AUTH_ERROR_MESSAGES[errorParam] ?? errorParam.replace(/_/g, ' ');
}

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

  getCurrentUser: async (token?: string): Promise<User> => {
    return apiFetch<User>('/auth/me', {
      ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
    });
  },

  upgradePlan: async (plan: PlanType): Promise<User> => {
    return apiFetch<User>('/auth/plan', {
      method: 'POST',
      body: JSON.stringify({ plan }),
    });
  },
};
