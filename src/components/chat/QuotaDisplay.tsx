import React from 'react';
import { Quota } from '../../types';
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
    <div className="flex items-center gap-5 text-[11px] font-bold uppercase tracking-widest">
      <div className="flex items-center gap-2">
        <span className="text-zinc-500/80">Requests</span>
        <span className={cn(
          isExhausted ? "text-red-500" : isNearLimit ? "text-amber-500" : "text-brand-cyan"
        )}>
          {quota.requestsRemaining} <span className="text-zinc-600">/ {quota.totalRequests}</span>
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-zinc-500/80">Tokens</span>
        <span className={cn(
          isExhausted ? "text-red-500" : isNearLimit ? "text-amber-500" : "text-brand-cyan"
        )}>
          {quota.tokensRemaining.toLocaleString()} <span className="text-zinc-600">/ {quota.totalTokens.toLocaleString()}</span>
        </span>
      </div>
    </div>
  );
};
