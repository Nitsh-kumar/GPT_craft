/// <reference types="vite/client" />

import { apiFetch, getAuthToken } from './api';
import { Message, Quota, Model } from '../types';

export const chatService = {
  getModels: async (): Promise<Model[]> => {
    // return apiFetch<Model[]>('/api/models');
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast and efficient', requiredPlan: 'free' },
          { id: 'gpt-4', name: 'GPT-4', description: 'Most capable model', requiredPlan: 'super' },
          { id: 'claude-3-opus', name: 'Claude 3 Opus', description: 'Powerful reasoning', requiredPlan: 'hyper' },
        ]);
      }, 500);
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
   * Handles the streaming of chat responses from the backend using the native Fetch API.
   * It uses an AbortController to allow the user to stop the generation mid-stream.
   */
  streamMessage: async (
    modelId: string,
    messages: Message[],
    onChunk: (chunk: string) => void,
    signal: AbortSignal
  ): Promise<void> => {
    const token = getAuthToken();
    
    // In a real application, you would fetch from your backend endpoint
    // const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat/stream`, {
    //   method: 'POST',
    //   headers: {
    //     'Content-Type': 'application/json',
    //     ...(token ? { Authorization: `Bearer ${token}` } : {}),
    //   },
    //   body: JSON.stringify({ model: modelId, messages }),
    //   signal,
    // });
    
    // if (!response.ok) {
    //   if (response.status === 401) throw new Error('Unauthorized');
    //   if (response.status === 429) throw new Error('Quota exceeded');
    //   throw new Error(`Server error: ${response.statusText}`);
    // }
    
    // if (!response.body) throw new Error('ReadableStream not supported');
    
    // const reader = response.body.getReader();
    // const decoder = new TextDecoder('utf-8');
    // let done = false;
    
    // while (!done) {
    //   const { value, done: readerDone } = await reader.read();
    //   done = readerDone;
    //   if (value) {
    //     // Decode the chunk and pass it to the callback
    //     // Note: SSE chunks might need parsing (e.g., splitting by "data: ")
    //     const chunkStr = decoder.decode(value, { stream: true });
    //     onChunk(chunkStr);
    //   }
    // }

    // Mock streaming implementation for demonstration
    return new Promise((resolve, reject) => {
      const mockResponse = "This is a simulated streaming response from the backend. It demonstrates how tokens are appended to the UI one by one without overwriting the state. It also shows how the scroll management works when new content arrives.";
      const words = mockResponse.split(' ');
      let i = 0;
      
      const interval = setInterval(() => {
        if (signal.aborted) {
          clearInterval(interval);
          reject(new DOMException('Aborted', 'AbortError'));
          return;
        }
        
        if (i < words.length) {
          onChunk((i > 0 ? ' ' : '') + words[i]);
          i++;
        } else {
          clearInterval(interval);
          resolve();
        }
      }, 50); // 50ms per word
      
      // Handle abort signal from outside
      signal.addEventListener('abort', () => {
        clearInterval(interval);
        reject(new DOMException('Aborted', 'AbortError'));
      });
    });
  },
};
