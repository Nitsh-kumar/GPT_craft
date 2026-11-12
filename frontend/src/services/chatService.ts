/// <reference types="vite/client" />

import { apiFetch, getAuthToken } from './api';
import { CraftMode, Message, Quota, Model, SseEventEnvelope, ApprovalRequiredEnvelope } from '../types';
import { parseSseBuffer } from '../utils/sseParser';

export const chatService = {
  getModels: async (): Promise<Model[]> => {
    try {
      return await apiFetch<Model[]>('/chat/models');
    } catch {
      return [
        {
          id: 'llama3-8b-8192',
          name: 'Llama 3 8B',
          description: 'Fast, efficient, and versatile for daily tasks.',
          requiredPlan: 'free',
        },
        {
          id: 'gemma-7b-it',
          name: 'Gemma 2 9B',
          description: 'Google-grade lightweight model optimization.',
          requiredPlan: 'free',
        },
        {
          id: 'mixtral-8x7b-32768',
          name: 'Mixtral 8x7B',
          description: 'Powerful mixture of experts for complex reasoning.',
          requiredPlan: 'super',
        },
        {
          id: 'llama3-70b-8192',
          name: 'Llama 3.3 70B',
          description: "Groq's most capable reasoning and coding model.",
          requiredPlan: 'hyper',
        },
      ];
    }
  },

  getQuota: async (): Promise<Quota> => {
    return apiFetch<Quota>('/chat/quota');
  },

  getConversations: async (): Promise<any[]> => {
    return apiFetch<any[]>('/chat/conversations');
  },

  getHistory: async (conversationId: string): Promise<Message[]> => {
    return apiFetch<Message[]>(`/chat/${conversationId}/history`);
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    await apiFetch<void>(`/chat/${conversationId}`, { method: 'DELETE' });
  },

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
    onEvent?: (event: SseEventEnvelope) => void
  ): Promise<{ conversationId: string }> => {
    const token = getAuthToken();
    const baseUrl =
      import.meta.env.VITE_API_BASE_URL !== undefined && import.meta.env.VITE_API_BASE_URL !== ''
        ? import.meta.env.VITE_API_BASE_URL
        : (typeof window !== 'undefined' ? window.location.origin : '');

    const lastUserMessage = messages.filter((m) => m.role === 'user').pop();
    if (!lastUserMessage) throw new Error('No user message found');

    const response = await fetch(`${baseUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message: lastUserMessage.content,
        conversation_id: conversationId ? parseInt(conversationId, 10) : null,
        model: modelId,
        mode,
      }),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized — please log in again.');
      if (response.status === 402) throw new Error('Daily token limit exceeded. Please upgrade your plan.');
      if (response.status === 403) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Selected model requires a higher subscription plan.');
      }
      if (response.status === 429) throw new Error('Rate limit exceeded. Please wait a moment.');
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.statusText}`);
    }

    let resolvedConversationId = conversationId || '';

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
            onChunk(event.content);
          } else if (event.type === 'token') {
            onChunk(event.token);
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
};
