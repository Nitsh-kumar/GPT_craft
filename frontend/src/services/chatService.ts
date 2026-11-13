import { apiFetch, getAuthToken } from './api';
import { CraftMode, Message, Quota, Model, ConversationResponse, HistoryMessage } from '../types';
import { readChatStream } from './stream';
import type { StreamStart } from './stream';

export const chatService = {
  getModels: (): Promise<Model[]> => apiFetch<Model[]>('/chat/models'),
  getQuota: (): Promise<Quota> => apiFetch<Quota>('/chat/quota'),
  getConversations: (): Promise<ConversationResponse[]> => apiFetch<ConversationResponse[]>('/chat/conversations'),
  getHistory: (id: string): Promise<HistoryMessage[]> => apiFetch<HistoryMessage[]>(`/chat/${id}/history`),
  deleteConversation: async (id: string): Promise<void> => { await apiFetch<void>(`/chat/${id}`, { method: 'DELETE' }); },

  streamMessage: async (
    conversationId: string | null, modelId: string, messages: Message[],
    onChunk: (chunk: string) => void, signal: AbortSignal, mode: CraftMode = 'standard',
    onStart?: (event: StreamStart) => void,
  ) => {
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
    const done = await readChatStream(response.body, event => {
      if (event.type === 'chunk') onChunk(event.content);
      if (event.type === 'start') onStart?.(event);
    });
    return { conversationId: String(done.conversation_id), modelUsed: done.model_used,
             modeUsed: done.mode_used as CraftMode };
  },
};
