import { useState, useEffect, useCallback } from 'react';
import { Quota } from '../types';
import { chatService } from '../services/chatService';

export const useQuota = () => {
  const [quota, setQuota] = useState<Quota | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await chatService.getQuota();
      setQuota(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch quota');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuota();
  }, [fetchQuota]);

  return { quota, isLoading, error, refreshQuota: fetchQuota };
};

