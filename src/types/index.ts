export type PlanType = 'free' | 'super' | 'hyper';

export interface User {
  id: string;
  email: string;
  name: string;
  plan: PlanType;
}

export interface AuthResponse {
  accessToken: string;
  user: User;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface Quota {
  requestsRemaining: number;
  tokensRemaining: number;
  totalRequests: number;
  totalTokens: number;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
}

export interface Model {
  id: string;
  name: string;
  description: string;
  requiredPlan: PlanType;
}
