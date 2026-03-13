import React from 'react';
import { Quota } from '../../types';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '../../utils/cn';

interface QuotaDisplayProps {
  quota: Quota | null;
  isLoading: boolean;
}

export const QuotaDisplay = ({ quota, isLoading }: QuotaDisplayProps) => {
  if (isLoading || !quota) return null;

  const isNearLimit = quota.requestsRemaining < 10 || quota.tokensRemaining < 5000;
  const isExhausted = quota.requestsRemaining <= 0 || quota.tokensRemaining <= 0;

  return (
    <div className="flex items-center gap-4 text-sm">
      <div className="flex items-center gap-1.5">
        <span className="text-zinc-500 dark:text-zinc-400">Requests:</span>
        <span className={cn(
          "font-medium",
          isExhausted ? "text-red-500" : isNearLimit ? "text-amber-500" : "text-emerald-500"
        )}>
          {quota.requestsRemaining} / {quota.totalRequests}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-zinc-500 dark:text-zinc-400">Tokens:</span>
        <span className={cn(
          "font-medium",
          isExhausted ? "text-red-500" : isNearLimit ? "text-amber-500" : "text-emerald-500"
        )}>
          {quota.tokensRemaining.toLocaleString()} / {quota.totalTokens.toLocaleString()}
        </span>
      </div>
      
      {isExhausted ? (
        <div className="flex items-center gap-1 text-red-500 bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded-md">
          <AlertCircle size={14} />
          <span className="text-xs font-medium">Quota Exceeded</span>
        </div>
      ) : isNearLimit ? (
        <div className="flex items-center gap-1 text-amber-500 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-md">
          <AlertCircle size={14} />
          <span className="text-xs font-medium">Near Limit</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-1 rounded-md hidden sm:flex">
          <CheckCircle2 size={14} />
          <span className="text-xs font-medium">Healthy</span>
        </div>
      )}
    </div>
  );
};
