import { apiFetch } from './api';
import { UserPreferences, UserMemoryItem, MemoryListResponse, MemoryCategory } from '../types';

export const PREFERENCES_UPDATED_EVENT = 'gptcraft:preferences-updated';

export const memoryService = {
  getPreferences: async (): Promise<UserPreferences> => {
    return apiFetch<UserPreferences>('/memory/preferences');
  },

  updatePreferences: async (data: {
    customInstructionsProfile?: string | null;
    customInstructionsStyle?: string | null;
    memoryEnabled?: boolean;
  }): Promise<UserPreferences> => {
    const updated = await apiFetch<UserPreferences>('/memory/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(PREFERENCES_UPDATED_EVENT, { detail: updated }));
    }
    return updated;
  },

  getMemories: async (): Promise<MemoryListResponse> => {
    return apiFetch<MemoryListResponse>('/memory');
  },

  addMemory: async (content: string, category: MemoryCategory = 'general'): Promise<UserMemoryItem> => {
    return apiFetch<UserMemoryItem>('/memory', {
      method: 'POST',
      body: JSON.stringify({ content, category }),
    });
  },

  deleteMemory: async (memoryId: number): Promise<void> => {
    await apiFetch<void>(`/memory/${memoryId}`, {
      method: 'DELETE',
    });
  },

  clearAllMemories: async (): Promise<{ message: string; count: number }> => {
    return apiFetch<{ message: string; count: number }>('/memory', {
      method: 'DELETE',
    });
  },
};
