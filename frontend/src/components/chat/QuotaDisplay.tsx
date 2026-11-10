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
  const tone = isExhausted ? 'text-danger' : isNearLimit ? 'text-warn' : 'text-ink';

  return (
    <div className="flex items-center gap-4 text-xs text-ink-3 tabular-nums" aria-label="Daily usage remaining">
      <div className="flex items-baseline gap-1.5">
        <span className={cn('font-medium', tone)}>{quota.requestsRemaining}</span>
        <span>/ {quota.totalRequests} requests</span>
      </div>
      <span className="h-3 w-px bg-line-strong" aria-hidden />
      <div className="flex items-baseline gap-1.5">
        <span className={cn('font-medium', tone)}>{quota.tokensRemaining.toLocaleString()}</span>
        <span>/ {quota.totalTokens.toLocaleString()} tokens</span>
      </div>
    </div>
  );
};
