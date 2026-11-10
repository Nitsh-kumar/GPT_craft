import { useState, useEffect, useCallback } from 'react';
import { Quota } from '../types';
import { chatService } from '../services/chatService';
import { useAuth } from '../context/AuthContext';

export const useQuota = () => {
  const { user } = useAuth();
  const [quota, setQuota] = useState<Quota | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await chatService.getQuota(user?.plan);
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
