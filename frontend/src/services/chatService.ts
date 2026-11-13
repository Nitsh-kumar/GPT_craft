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
import { parseSseBuffer } from '../utils/sseParser';
import { readChatStream } from './stream';
import type { StreamStart } from './stream';

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
    signal?: AbortSignal
  ): Promise<{ conversationId?: string }> => {
    const token = getAuthToken();
    const baseUrl =
      import.meta.env.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== ''
        ? import.meta.env.VITE_API_BASE_URL
        : (typeof window !== 'undefined' ? window.location.origin : '');

    const response = await fetch(`${baseUrl}/chat/approval`, {
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
      if (response.status === 401) throw new Error('Unauthorized — please log in again.');
      if (response.status === 402) throw new Error('Daily token limit exceeded. Please upgrade your plan.');
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.statusText}`);
    }

    let resolvedConversationId = '';

    if (response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        const decoded = done ? decoder.decode() : decoder.decode(value, { stream: true });
        const { events, remaining } = parseSseBuffer(buffer, decoded, done);
        buffer = remaining;

        for (const event of events) {
          onEvent?.(event);
          if (event.type === 'chunk') {
            onChunk?.(event.content);
          } else if (event.type === 'token') {
            onChunk?.(event.token);
          } else if (event.type === 'done' && event.conversationId) {
            resolvedConversationId = event.conversationId;
          } else if (event.type === 'error') {
            throw new Error(event.error);
          }
        }

        if (done) break;
      }
    }

    return { conversationId: resolvedConversationId };
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
    const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
    const response = await fetch(new URL('/chat/stream', base), {
      method: 'POST', signal,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ message: last.content, conversation_id: conversationId ? Number(conversationId) : null,
                            model: modelId, mode, request_id: crypto.randomUUID() }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if (response.status === 401) window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      const retryAfter = response.headers.get('Retry-After');
      throw new Error((data.detail || 'Unable to start generation.') + (retryAfter ? ` Retry after ${retryAfter} seconds.` : ''));
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

    let resolvedConversationId = conversationId || '';
    let resolvedModelUsed: string | undefined;
    let resolvedModeUsed: CraftMode | undefined;
    let sawDone = false;

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        const decoded = done ? decoder.decode() : decoder.decode(value, { stream: true });
        const { events, remaining } = parseSseBuffer(buffer, decoded, done);
        buffer = remaining;

        for (const event of events) {
          onEvent?.(event);
          if (event.type === 'chunk') {
            onChunk(event.content);
          } else if (event.type === 'token') {
            onChunk(event.token);
          } else if (event.type === 'done') {
            sawDone = true;
            if (event.conversationId) resolvedConversationId = event.conversationId;
            if (event.modelUsed) resolvedModelUsed = event.modelUsed;
            if (event.modeUsed) resolvedModeUsed = event.modeUsed as CraftMode;
          } else if (event.type === 'error') {
            throw new Error(event.error);
          }
        }

        if (done) break;
      }
      if (!sawDone) {
        throw new Error('Generation was interrupted before completion. Please retry.');
      }
    } finally {
      await reader.cancel().catch(() => undefined);
      reader.releaseLock();
    }

    return {
      conversationId: resolvedConversationId,
      modelUsed: resolvedModelUsed,
      modeUsed: resolvedModeUsed,
    };
  },
};
