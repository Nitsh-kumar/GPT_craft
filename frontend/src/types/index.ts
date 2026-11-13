export type PlanType = 'free' | 'super' | 'hyper';

export type CraftMode = 'standard' | 'architect' | 'code' | 'brainstorm' | 'agent';

export type SseEventEnvelope =
  | { type: 'thought'; thought: string }
  | { type: 'token'; token: string }
  | { type: 'action_call'; actionId: string; tool: string; args: Record<string, unknown>; tier: number }
  | {
      type: 'approval_required';
      actionId: string;
      tool: string;
      tier: number;
      parameters: Record<string, unknown>;
      rationale: string;
      diff?: string;
    }
  | {
      type: 'action_result';
      actionId: string;
      tool: string;
      output: string;
      durationMs?: number;
      latencyMs?: number;
      exitCode?: number;
      status?: string;
    }
  | { type: 'chunk'; content: string }
  | {
      type: 'done';
      status?: string;
      totalSteps?: number;
      conversationId?: string;
      tokensUsed?: number;
      tokensRemaining?: number;
      modelUsed?: string;
      modeUsed?: string;
    }
  | { type: 'error'; error: string };

export interface ApprovalRequiredEnvelope {
  actionId: string;
  tool: string;
  tier: number;
  parameters: Record<string, unknown>;
  rationale: string;
  diff?: string;
}

export interface ApprovalDecisionPayload {
  actionId: string;
  decision: 'approve' | 'modify' | 'reject';
  modifiedParams?: Record<string, unknown>;
  feedback?: string;
}

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

export interface AgentActionTelemetry {
  actionId: string;
  tool: string;
  args: Record<string, unknown>;
  tier: number;
  output?: string;
  status?: 'running' | 'completed' | 'failed' | 'aborted';
  durationMs?: number;
  startTime?: number;
  exitCode?: number;
  error?: string;
}

export type AgentActionItem = AgentActionTelemetry;

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  mode?: CraftMode;
  modelUsed?: string;
  modeUsed?: CraftMode;
  status?: 'streaming' | 'complete' | 'interrupted';
  thoughts?: string[];
  actions?: AgentActionTelemetry[];
  approvalRequired?: ApprovalRequiredEnvelope;
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
