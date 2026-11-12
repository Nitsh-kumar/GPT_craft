import React, { useState } from 'react';
import { Message, CraftMode } from '../../types';
import { cn } from '../../utils/cn';
import { Copy, Check, Terminal, Sparkles, Compass, Code2, Lightbulb, Bot, Wrench } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ApprovalCard } from './ApprovalCard';

interface MessageBubbleProps {
  message: Message;
  modelName?: string;
  modeName?: CraftMode;
  onApprovalDecision?: (
    actionId: string,
    decision: 'approve' | 'modify' | 'reject',
    modifiedParams?: Record<string, unknown>,
    feedback?: string
  ) => void;
}

const getModeMeta = (mode?: CraftMode) => {
  switch (mode) {
    case 'agent':
      return {
        label: 'Agent Studio',
        badge: 'AGENT',
        icon: <Bot size={12} className="text-accent" />,
        pillClass: 'border-accent/35 bg-accent-soft text-accent',
      };
    case 'architect':
      return { label: 'Deep Architect', icon: <Compass size={12} className="text-blue-500" />, pillClass: 'border-line bg-raised text-ink-3' };
    case 'code':
      return { label: 'Code Craft', icon: <Code2 size={12} className="text-emerald-500" />, pillClass: 'border-line bg-raised text-ink-3' };
    case 'brainstorm':
      return { label: 'Brainstorm', icon: <Lightbulb size={12} className="text-amber-500" />, pillClass: 'border-line bg-raised text-ink-3' };
    case 'standard':
    default:
      return { label: 'Standard Craft', icon: <Sparkles size={12} className="text-accent" />, pillClass: 'border-line bg-raised text-ink-3' };
  }
};

export const MessageBubble = ({
  message,
  modelName = 'GPTCraft Engine',
  modeName = 'standard',
  onApprovalDecision,
}: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const time = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const effectiveMode = message.mode || modeName;
  const modeMeta = getModeMeta(effectiveMode);

  if (isUser) {
    return (
      <div className="group flex w-full animate-in flex-col items-end py-2">
        <div className="flex items-center gap-2 mb-1 px-1">
          <span className="text-[11px] font-mono text-ink-3">Prompt</span>
          <time className="text-[10px] text-ink-3 tabular-nums opacity-0 group-hover:opacity-100 transition-opacity">
            {time}
          </time>
        </div>
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-line-strong bg-raised px-4 py-3 text-[0.95rem] leading-relaxed text-ink shadow-lift sm:max-w-[75%]">
          <div className="prose-craft">
            <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
          </div>
        </div>
      </div>
    );
  }

  const hasThoughts = Boolean(message.thoughts && message.thoughts.length > 0);
  const hasActions = Boolean(message.actions && message.actions.length > 0);
  const hasApproval = Boolean(message.approvalRequired);
  if (!message.content && !hasThoughts && !hasActions && !hasApproval) return null;

  return (
    <div className="group flex w-full animate-in flex-col rounded-xl border border-line bg-surface/60 p-4 sm:p-5 shadow-lift transition-colors hover:border-line-strong">
      {/* Assistant Meta Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-line text-xs">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-line bg-raised">
            <img src="/craft_logo.png" alt="GPTCraft" className="h-3.5 w-3.5 object-contain" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="font-display font-semibold text-ink text-xs">GPTCraft</span>
            <span className="text-line-strong">·</span>
            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-sunken border border-line text-ink-2">
              {modelName}
            </span>
            <span
              data-testid="message-mode-badge"
              className={cn('inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded border', modeMeta.pillClass)}
            >
              {modeMeta.icon}
              <span>{modeMeta.label}</span>
              {modeMeta.badge && (
                <span className="rounded bg-accent text-on-accent px-1 py-px font-mono text-[9px] font-semibold tracking-wider">
                  {modeMeta.badge}
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Action controls */}
        <div className="flex items-center gap-2 text-ink-3">
          <button
            onClick={handleCopy}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-mono border border-line bg-raised transition-colors hover:text-ink hover:border-line-strong',
              copied && 'text-ok border-ok/40 bg-ok/10'
            )}
            title="Copy message text"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
          <time className="text-[11px] font-mono tabular-nums">{time}</time>
        </div>
      </div>

      {/* Agent Thought Envelopes */}
      {hasThoughts && (
        <div
          data-testid="agent-thought-trace"
          className="mb-3 space-y-1 rounded-lg border border-line bg-sunken px-3 py-2 font-mono text-xs text-ink-2"
        >
          {message.thoughts!.map((thought, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <Bot size={13} className="mt-0.5 shrink-0 text-accent" />
              <span>{thought}</span>
            </div>
          ))}
        </div>
      )}

      {/* Agent Action Telemetry */}
      {hasActions && (
        <div
          data-testid="agent-action-telemetry"
          className="mb-3 space-y-2 rounded-lg border border-line bg-sunken p-3 font-mono text-xs text-ink-2"
        >
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-accent uppercase tracking-wider">
            <Wrench size={12} className="text-accent" />
            <span>Agent Workspace Actions</span>
          </div>
          {message.actions!.map((action, idx) => (
            <div
              key={action.actionId || idx}
              data-testid={`action-telemetry-item-${action.tool}`}
              className="rounded-md border border-line bg-raised/70 p-2 text-xs"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 font-medium text-ink">
                  <span className="text-accent font-mono text-[11px]">{action.tool}</span>
                  <span className="rounded bg-accent/15 text-accent border border-accent/25 px-1 py-0.5 font-mono text-[9px] font-semibold">
                    Tier {action.tier}
                  </span>
                </div>
                <span className="text-[10px] text-ink-3">
                  {action.output !== undefined ? 'Completed' : 'Running...'}
                </span>
              </div>
              {action.args && Object.keys(action.args).length > 0 && (
                <div className="mt-1 text-[11px] text-ink-3">
                  <span className="text-ink-2">args:</span> {JSON.stringify(action.args)}
                </div>
              )}
              {action.output !== undefined && (
                <div className="mt-1.5 rounded border border-line/60 bg-sunken/80 p-1.5 text-[11px] text-ink-2 overflow-x-auto max-h-36">
                  <pre className="whitespace-pre-wrap">{action.output}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Human-In-The-Loop Approval Card */}
      {message.approvalRequired && (
        <ApprovalCard
          approval={message.approvalRequired}
          onDecision={onApprovalDecision || (() => {})}
        />
      )}

      {/* Structured Content Stream */}
      <div className="min-w-0 flex-1">
        <div className="prose-craft">
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              pre: ({ children, ...props }) => (
                <div className="relative group/code my-3 overflow-hidden rounded-xl border border-line bg-sunken">
                  <div className="flex items-center justify-between border-b border-line bg-raised/50 px-3 py-1.5 text-[11px] font-mono text-ink-3">
                    <span className="flex items-center gap-1.5">
                      <Terminal size={12} className="text-accent" />
                      Code Snippet
                    </span>
                  </div>
                  <pre {...props} className="p-3.5 overflow-x-auto text-[0.84rem] font-mono">
                    {children}
                  </pre>
                </div>
              ),
            }}
          >
            {message.content}
          </Markdown>
        </div>
      </div>
    </div>
  );
};
