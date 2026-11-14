import { apiFetch, getAuthToken } from './api';
import {
  CraftMode,
  Message,
  Quota,
  Model,
  SseEventEnvelope,
  ApprovalRequiredEnvelope,
  ConversationResponse,
  HistoryMessage,
} from '../types';
import { readAgentStream, readChatStream } from './stream';
import type { StreamStart } from './stream';

function resolveApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== ''
    ? import.meta.env.VITE_API_BASE_URL
    : (typeof window !== 'undefined' ? window.location.origin : '');
}

async function throwStreamHttpError(response: Response, fallbackMessage: string): Promise<never> {
  if (response.status === 401 && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
  }
  const errData = await response.json().catch(() => ({}));
  if (response.status === 401) {
    throw new Error(errData.detail || 'Unauthorized — please log in again.');
  }
  if (response.status === 402) {
    throw new Error(errData.detail || 'Daily token limit exceeded. Please upgrade your plan.');
  }
  const retryAfter = response.headers.get('Retry-After');
  throw new Error(
    (errData.detail || fallbackMessage) + (retryAfter ? ` Retry after ${retryAfter} seconds.` : '')
  );
}

export const chatService = {
  getModels: (): Promise<Model[]> => apiFetch<Model[]>('/chat/models'),
  getQuota: (): Promise<Quota> => apiFetch<Quota>('/chat/quota'),
  getConversations: (): Promise<ConversationResponse[]> => apiFetch<ConversationResponse[]>('/chat/conversations'),
  getHistory: (id: string): Promise<HistoryMessage[]> => apiFetch<HistoryMessage[]>(`/chat/${id}/history`),
  deleteConversation: async (id: string): Promise<void> => { await apiFetch<void>(`/chat/${id}`, { method: 'DELETE' }); },

  getPendingApproval: async (conversationId: string): Promise<ApprovalRequiredEnvelope | null> => {
    try {
      return await apiFetch<ApprovalRequiredEnvelope | null>(`/chat/${conversationId}/approval`);
    } catch {
      return null;
    }
  },

  submitApproval: async (
    actionId: string,
    decision: 'approve' | 'modify' | 'reject',
    modifiedParams?: Record<string, unknown>,
    feedback?: string,
    onChunk?: (chunk: string) => void,
    onEvent?: (event: SseEventEnvelope) => void,
    signal?: AbortSignal,
    onStreamStart?: () => void
  ): Promise<{ conversationId: string; modelUsed?: string; modeUsed?: CraftMode }> => {
    const token = getAuthToken();
    const response = await fetch(`${resolveApiBaseUrl()}/chat/approval`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        actionId,
        decision,
        modifiedParams,
        feedback,
      }),
      signal,
    });

    if (!response.ok) {
      await throwStreamHttpError(response, `Server error: ${response.statusText}`);
    }
    if (!response.body) {
      throw new Error('The server returned no response stream.');
    }

    onStreamStart?.();
    return readAgentStream(response.body, { onChunk, onEvent });
  },

  streamMessage: async (
    conversationId: string | null,
    modelId: string,
    messages: Message[],
    onChunk: (chunk: string) => void,
    signal: AbortSignal,
    mode: CraftMode = 'standard',
    onEvent?: (event: SseEventEnvelope) => void,
    onStart?: (event: StreamStart) => void
  ): Promise<{ conversationId: string; modelUsed?: string; modeUsed?: CraftMode }> => {
    const token = getAuthToken();
    const last = messages.filter(message => message.role === 'user').pop();
    if (!last) throw new Error('No user message found');
    const base = resolveApiBaseUrl();
    const response = await fetch(new URL('/chat/stream', base), {
      method: 'POST', signal,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ message: last.content, conversation_id: conversationId ? Number(conversationId) : null,
                            model: modelId, mode, request_id: crypto.randomUUID() }),
    });
    if (!response.ok) {
      await throwStreamHttpError(response, 'Unable to start generation.');
    }
    if (!response.body) throw new Error('The server returned no response stream.');

    if (mode !== 'agent') {
      const done = await readChatStream(response.body, event => {
        if (event.type === 'chunk') onChunk(event.content);
        if (event.type === 'start') onStart?.(event);
      });
      return {
        conversationId: String(done.conversation_id),
        modelUsed: done.model_used,
        modeUsed: done.mode_used as CraftMode,
      };
    }

    return readAgentStream(response.body, {
      onChunk,
      onEvent,
      initialConversationId: conversationId || '',
    });
  },
};
