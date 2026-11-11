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

export type MemoryCategory = 'general' | 'tech_stack' | 'project' | 'preference';

export interface UserPreferences {
  userId: number;
  customInstructionsProfile?: string | null;
  customInstructionsStyle?: string | null;
  memoryEnabled: boolean;
  updatedAt?: string | null;
}

export interface UserMemoryItem {
  id: number;
  userId: number;
  category: MemoryCategory;
  content: string;
  isActive: boolean;
  sourceConversationId?: number | null;
  createdAt: string;
  updatedAt?: string | null;
}

export interface MemoryListResponse {
  memories: UserMemoryItem[];
  total: number;
  memoryEnabled: boolean;
}
