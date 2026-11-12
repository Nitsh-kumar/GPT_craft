export type PlanType = 'free' | 'super' | 'hyper';

export type CraftMode = 'standard' | 'architect' | 'code' | 'brainstorm';

export interface User {
  id: string | number;
  email: string;
  name: string;
  plan: PlanType;
}

export interface AuthResponse {
  accessToken: string;
  tokenType?: string;
  user: User;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  modelUsed?: string;
  modeUsed?: CraftMode;
  status?: 'streaming' | 'complete' | 'interrupted';
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

// Existing HTTP history fields remain snake_case for compatibility.
export interface ConversationResponse {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}
export interface HistoryMessage {
  id: number;
  role: Message['role'];
  content: string;
  created_at: string;
  model_used?: string | null;
  mode_used?: CraftMode | null;
}
