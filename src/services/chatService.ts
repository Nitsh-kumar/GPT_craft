/// <reference types="vite/client" />

import { apiFetch, getAuthToken } from './api';
import { Message, Quota, Model } from '../types';

export const chatService = {
  getModels: async (): Promise<Model[]> => {
    // return apiFetch<Model[]>('/api/models');
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          { 
            id: 'llama3-8b-8192', 
            name: 'Llama 3 8B', 
            description: 'Fast, efficient, and versatile for daily tasks.', 
            requiredPlan: 'free' 
          },
          { 
            id: 'gemma-7b-it', 
            name: 'Gemma 7B', 
            description: 'Google-grade lightweight model optimization.', 
            requiredPlan: 'free' 
          },
          { 
            id: 'mixtral-8x7b-32768', 
            name: 'Mixtral 8x7B', 
            description: 'Powerful mixture of experts for complex reasoning.', 
            requiredPlan: 'super' 
          },
          { 
            id: 'llama3-70b-8192', 
            name: 'Llama 3 70B', 
            description: 'Groq\'s most capable reasoning and coding model.', 
            requiredPlan: 'hyper' 
          },
        ]);
      }, 300);
    });
  },

  getQuota: async (plan: string = 'free'): Promise<Quota> => {
    // return apiFetch<Quota>('/api/quota');
    return new Promise((resolve) => {
      setTimeout(() => {
        const quotas = {
          free: { requestsRemaining: 50, tokensRemaining: 100000, totalRequests: 50, totalTokens: 100000 },
          super: { requestsRemaining: 500, tokensRemaining: 1000000, totalRequests: 500, totalTokens: 1000000 },
          hyper: { requestsRemaining: 5000, tokensRemaining: 10000000, totalRequests: 5000, totalTokens: 10000000 },
        };
        resolve(quotas[plan as keyof typeof quotas] || quotas.free);
      }, 500);
    });
  },

  getHistory: async (sessionId: string): Promise<Message[]> => {
    // return apiFetch<Message[]>(`/api/chat/${sessionId}/history`);
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([]);
      }, 500);
    });
  },

  /**
   * streamMessage
   * 
   * Sends a chat message to the real backend API.
   * The backend returns a full response (non-streaming), so we simulate
   * word-by-word streaming on the frontend for a smooth UX.
   */
  streamMessage: async (
    modelId: string,
    messages: Message[],
    onChunk: (chunk: string) => void,
    signal: AbortSignal
  ): Promise<void> => {
    const token = getAuthToken();
    
    // Get the last user message to send to the backend
    const lastUserMessage = messages.filter(m => m.role === 'user').pop();
    if (!lastUserMessage) throw new Error('No user message found');

    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message: lastUserMessage.content }),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized — please log in again.');
      if (response.status === 402) throw new Error('Daily token limit exceeded. Please upgrade your plan.');
      if (response.status === 429) throw new Error('Rate limit exceeded. Please wait a moment.');
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server error: ${response.statusText}`);
    }

    const data = await response.json();
    const fullResponse: string = data.response;

    // Simulate streaming for smooth UX
    const words = fullResponse.split(' ');
    for (let i = 0; i < words.length; i++) {
      if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
      onChunk((i > 0 ? ' ' : '') + words[i]);
      await new Promise(resolve => setTimeout(resolve, 20));
    }
  },
};
