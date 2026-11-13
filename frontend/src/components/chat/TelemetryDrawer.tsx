import React, { useState } from 'react';
import {
  ChevronDown,
  Terminal,
  Wrench,
  Bot,
  Check,
  Copy,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  CornerDownRight,
} from 'lucide-react';
import type { AgentActionTelemetry } from '../../types';
import { cn } from '../../utils/cn';
import {
  formatLatency,
  getToolTierMeta,
  detectActionStatus,
} from '../../utils/telemetry';

export interface TelemetryDrawerProps {
  thoughts?: string[];
  actions?: AgentActionTelemetry[];
  isStreaming?: boolean;
  defaultExpanded?: boolean;
  className?: string;
}

export const TelemetryDrawer: React.FC<TelemetryDrawerProps> = ({
  thoughts = [],
  actions = [],
  isStreaming = false,
  defaultExpanded = false,
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copiedActionId, setCopiedActionId] = useState<string | null>(null);

  const totalActions = actions.length;
  const totalThoughts = thoughts.length;

  if (totalActions === 0 && totalThoughts === 0) {
    return null;
  }

  const isRunning =
    isStreaming ||
    actions.some((a) => a.output === undefined && a.status !== 'aborted');

  const hasFailures = actions.some(
    (a) => detectActionStatus(a).isError && a.status !== 'aborted'
  );

  const totalDurationMs = actions.reduce<number>((sum, a) => {
    return sum + (typeof a.durationMs === 'number' ? a.durationMs : 0);
  }, 0);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedActionId(id);
    setTimeout(() => {
      setCopiedActionId(null);
    }, 2000);
  };

  return (
    <div
      data-testid="telemetry-drawer"
      className={cn(
        'overflow-hidden rounded-xl border border-line bg-surface/90 shadow-sm transition-[border-color,box-shadow]',
        isRunning && 'border-accent/40 shadow-lift',
        className
      )}
    >
      {/* Compact Summary Bar (Always Visible, Click to Toggle) */}
      <button
        type="button"
        data-testid="telemetry-drawer-toggle"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 bg-sunken/40 px-3.5 py-2.5 text-left transition-colors hover:bg-sunken/70"
      >
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          {/* Status Indicator */}
          <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-raised border border-line">
            {isRunning ? (
              <Loader2 size={12} className="animate-spin text-accent" />
            ) : hasFailures ? (
              <AlertCircle size={12} className="text-danger" />
            ) : (
              <CheckCircle2 size={12} className="text-ok" />
            )}
          </div>

          <span className="font-mono text-xs font-semibold text-ink">
            Agent Telemetry
          </span>

          {/* Quick Counter Chips */}
          {totalActions > 0 && (
            <span
              data-testid="telemetry-actions-count"
              className="rounded border border-line bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-2"
            >
              {totalActions} {totalActions === 1 ? 'tool call' : 'tool calls'}
            </span>
          )}

          {totalThoughts > 0 && (
            <span
              data-testid="telemetry-thoughts-count"
              className="rounded border border-line bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-2"
            >
              {totalThoughts} {totalThoughts === 1 ? 'thought' : 'thoughts'}
            </span>
          )}

          {/* Capability Tier Badges in Summary */}
          {actions.some((a) => a.tier >= 2) && (
            <span className="rounded border border-warn/30 bg-warn/15 px-1.5 py-0.5 font-mono text-[9px] font-semibold text-warn">
              Tier 2 Mutation
            </span>
          )}

          {actions.some((a) => a.tier === 1) && (
            <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 font-mono text-[9px] font-semibold text-accent">
              Tier 1 Read-Only
            </span>
          )}

          {/* Latency Timing Badge */}
          {totalDurationMs > 0 && (
            <span
              data-testid="telemetry-total-latency"
              className="inline-flex items-center gap-1 rounded border border-line bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-3"
            >
              <Clock size={10} />
              {formatLatency(totalDurationMs)}
            </span>
          )}
        </div>

        {/* Right Controls */}
        <div className="flex shrink-0 items-center gap-2">
          <span
            data-testid="telemetry-status-badge"
            className={cn(
              'rounded-full px-2 py-0.5 font-mono text-[10px] font-medium border',
              isRunning
                ? 'border-accent/30 bg-accent/10 text-accent animate-pulse'
                : hasFailures
                  ? 'border-danger/30 bg-danger/10 text-danger'
                  : 'border-ok/30 bg-ok/10 text-ok'
            )}
          >
            {isRunning ? 'Running' : hasFailures ? 'Failed' : 'Completed'}
          </span>

          <span className="flex items-center gap-1 font-mono text-[11px] text-ink-3">
            <span>{isExpanded ? 'Hide' : 'Logs'}</span>
            <ChevronDown
              size={13}
              className={cn(
                'text-ink-3 transition-transform duration-200',
                isExpanded && 'rotate-180 text-ink'
              )}
            />
          </span>
        </div>
      </button>

      {/* Expanded Logs Drawer */}
      {isExpanded && (
        <div className="space-y-3.5 border-t border-line bg-surface p-3.5 text-xs">
          {/* Model Reasoning / Thought Trace */}
          {totalThoughts > 0 && (
            <div data-testid="agent-thought-trace" className="space-y-1.5">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-accent">
                <Bot size={13} />
                <span>Model Reasoning Trace ({totalThoughts})</span>
              </div>
              <div className="space-y-1.5 rounded-lg border border-line bg-sunken/60 p-2.5 font-mono text-xs text-ink-2">
                {thoughts.map((thought, idx) => (
                  <div key={idx} className="flex items-start gap-2 leading-relaxed">
                    <span className="shrink-0 text-accent select-none font-semibold">
                      #{idx + 1}
                    </span>
                    <CornerDownRight
                      size={12}
                      className="mt-1 shrink-0 text-ink-3"
                    />
                    <span className="flex-1 whitespace-pre-wrap">{thought}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tool Calls & Execution Results */}
          {totalActions > 0 && (
            <div data-testid="agent-action-telemetry" className="space-y-2.5">
              <div className="flex items-center justify-between font-mono text-[11px] font-semibold uppercase tracking-wider text-accent">
                <span className="flex items-center gap-1.5">
                  <Wrench size={13} />
                  <span>Workspace Tool Executions ({totalActions})</span>
                </span>
                <span className="text-[10px] text-ink-3 normal-case">
                  Detailed stdout / stderr & timing
                </span>
              </div>

              <div className="space-y-2">
                {actions.map((action, idx) => {
                  const statusInfo = detectActionStatus(action);
                  const tierMeta = getToolTierMeta(action.tier);
                  const durationStr = formatLatency(action.durationMs);
                  const actionKey = action.actionId || `act_${idx}`;
                  const isCopied = copiedActionId === actionKey;

                  return (
                    <div
                      key={actionKey}
                      data-testid={`action-telemetry-item-${action.tool}`}
                      className="rounded-lg border border-line bg-raised p-3 shadow-xs"
                    >
                      {/* Action Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-line/60">
                        <div className="flex items-center gap-2">
                          <Terminal size={13} className="text-accent shrink-0" />
                          <span className="font-mono text-xs font-semibold text-ink">
                            {action.tool}
                          </span>
                          {/* Capability Tier Badge */}
                          <span
                            data-testid={`tier-badge-${action.tool}`}
                            className={cn(
                              'rounded px-1.5 py-0.5 font-mono text-[9px] font-semibold border',
                              tierMeta.badgeClass
                            )}
                          >
                            {tierMeta.shortLabel}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {/* Latency badge */}
                          {durationStr && (
                            <span
                              data-testid={`latency-badge-${action.tool}`}
                              className="inline-flex items-center gap-1 rounded bg-sunken px-1.5 py-0.5 font-mono text-[10px] text-ink-3 border border-line"
                            >
                              <Clock size={10} />
                              {durationStr}
                            </span>
                          )}

                          {/* Status / Exit code badge */}
                          <span
                            data-testid={`status-badge-${action.tool}`}
                            className={cn(
                              'rounded px-1.5 py-0.5 font-mono text-[10px] font-medium border',
                              statusInfo.status === 'running'
                                ? 'border-accent/30 bg-accent/10 text-accent animate-pulse'
                                : statusInfo.isError
                                  ? 'border-danger/30 bg-danger/10 text-danger'
                                  : 'border-ok/30 bg-ok/10 text-ok'
                            )}
                          >
                            {statusInfo.statusLabel}
                          </span>
                        </div>
                      </div>

                      {/* Parameters */}
                      {action.args && Object.keys(action.args).length > 0 && (
                        <div className="mt-2 text-[11px]">
                          <span className="font-mono font-medium text-ink-3 uppercase text-[9px] tracking-wider block mb-1">
                            Parameters
                          </span>
                          <div className="rounded border border-line bg-sunken/70 p-2 font-mono text-ink-2 overflow-x-auto max-h-32">
                            <pre className="whitespace-pre-wrap">
                              {JSON.stringify(action.args, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Tool Result: stdout / stderr / error */}
                      {action.output !== undefined && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono font-medium text-ink-3 uppercase text-[9px] tracking-wider">
                              Output & Results
                            </span>
                            <button
                              type="button"
                              onClick={() => handleCopy(action.output || '', actionKey)}
                              data-testid={`copy-output-${action.tool}`}
                              className="flex items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[10px] text-ink-3 hover:text-ink hover:bg-sunken border border-transparent hover:border-line transition-colors"
                            >
                              {isCopied ? (
                                <>
                                  <Check size={10} className="text-ok" />
                                  <span className="text-ok font-semibold">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={10} />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>

                          <div
                            className={cn(
                              'rounded border bg-sunken p-2.5 font-mono text-[11px] leading-relaxed overflow-x-auto max-h-48',
                              statusInfo.isError
                                ? 'border-danger/30 text-danger/95'
                                : 'border-line text-ink-2'
                            )}
                          >
                            <pre className="whitespace-pre-wrap">{action.output}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
