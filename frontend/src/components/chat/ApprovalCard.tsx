import React, { useState } from 'react';
import {
  ShieldAlert,
  Check,
  X,
  Edit3,
  FileCode,
  Terminal,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Copy,
} from 'lucide-react';
import { ApprovalRequiredEnvelope } from '../../types';
import { cn } from '../../utils/cn';
import { parseUnifiedDiff } from '../../utils/telemetry';

interface ApprovalCardProps {
  approval: ApprovalRequiredEnvelope;
  onDecision: (
    actionId: string,
    decision: 'approve' | 'modify' | 'reject',
    modifiedParams?: Record<string, unknown>,
    feedback?: string
  ) => void;
  disabled?: boolean;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  approval,
  onDecision,
  disabled = false,
}) => {
  const isCommand = Boolean(
    approval.tool === 'run_terminal_command' ||
    approval.parameters.command !== undefined
  );
  const initialCommand = String(approval.parameters.command || '');

  const [mode, setMode] = useState<'view' | 'modify' | 'reject'>('view');
  const [modifiedPath, setModifiedPath] = useState(String(approval.parameters.path || ''));
  const [modifiedContent, setModifiedContent] = useState(String(approval.parameters.content || ''));
  const [modifiedCommand, setModifiedCommand] = useState(initialCommand);
  const [feedback, setFeedback] = useState('');
  const [showFullDiff, setShowFullDiff] = useState(true);
  const [commandCopied, setCommandCopied] = useState(false);

  const parsedDiff = parseUnifiedDiff(approval.diff);

  const handleCopyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCommandCopied(true);
    setTimeout(() => setCommandCopied(false), 2000);
  };

  const handleApprove = () => {
    onDecision(approval.actionId, 'approve');
  };

  const handleConfirmModify = () => {
    if (isCommand) {
      onDecision(
        approval.actionId,
        'modify',
        {
          command: modifiedCommand,
        }
      );
    } else {
      onDecision(
        approval.actionId,
        'modify',
        {
          path: modifiedPath,
          content: modifiedContent,
          mode: approval.parameters.mode || 'write',
        }
      );
    }
    setMode('view');
  };

  const handleConfirmReject = () => {
    onDecision(approval.actionId, 'reject', undefined, feedback.trim() || 'Action rejected by user');
    setMode('view');
  };

  return (
    <div
      data-testid="approval-card"
      className="my-3 overflow-hidden rounded-xl border border-warn/40 bg-surface/80 shadow-lift"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-warn/10 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-warn/20 text-warn">
            <ShieldAlert size={14} />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-ink">
              {approval.tool}
            </span>
            <span className="rounded border border-warn/30 bg-warn/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-warn">
              Tier {approval.tier} HITL
            </span>
          </div>
        </div>
        <span className="font-mono text-[11px] text-warn font-medium">
          Approval Required
        </span>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3 text-xs">
        {/* Rationale */}
        <div>
          <span className="font-semibold text-ink-3 uppercase text-[10px] tracking-wider block mb-1">
            Rationale
          </span>
          <p className="text-ink text-sm leading-relaxed bg-raised/50 p-2.5 rounded-lg border border-line">
            {approval.rationale || (isCommand ? 'Running terminal command' : 'Mutating workspace file')}
          </p>
        </div>

        {/* Target Path or Shell Command */}
        {isCommand ? (
          <div className="flex items-center gap-2 font-mono text-xs bg-sunken/60 px-3 py-1.5 rounded-lg border border-line">
            <Terminal size={13} className="text-accent shrink-0" />
            <span className="text-ink-3">Command:</span>
            <span className="text-ink font-medium truncate">{initialCommand}</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 font-mono text-xs bg-sunken/60 px-3 py-1.5 rounded-lg border border-line">
            <FileCode size={13} className="text-accent shrink-0" />
            <span className="text-ink-3">Target:</span>
            <span className="text-ink font-medium truncate">{String(approval.parameters.path || 'Unknown')}</span>
          </div>
        )}

        {/* Diff Preview / Modification Editor */}
        {mode === 'modify' ? (
          <div className="space-y-2 border border-line rounded-lg bg-raised p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-xs text-accent">
                {isCommand ? 'Modify Shell Command' : 'Modify Target Content'}
              </span>
              <span className="text-[11px] text-ink-3">
                {isCommand ? 'Edit command line below' : 'Edit file content below'}
              </span>
            </div>
            {isCommand ? (
              <div>
                <label className="block text-[11px] text-ink-3 mb-1 font-mono">Shell Command:</label>
                <input
                  type="text"
                  value={modifiedCommand}
                  onChange={(e) => setModifiedCommand(e.target.value)}
                  className="w-full rounded border border-line bg-sunken px-2.5 py-1.5 font-mono text-xs text-ink focus:border-accent focus:outline-none"
                />
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-[11px] text-ink-3 mb-1 font-mono">File Path:</label>
                  <input
                    type="text"
                    value={modifiedPath}
                    onChange={(e) => setModifiedPath(e.target.value)}
                    className="w-full rounded border border-line bg-sunken px-2.5 py-1.5 font-mono text-xs text-ink focus:border-accent focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-ink-3 mb-1 font-mono">New Content:</label>
                  <textarea
                    value={modifiedContent}
                    onChange={(e) => setModifiedContent(e.target.value)}
                    rows={8}
                    className="w-full rounded border border-line bg-sunken p-2.5 font-mono text-xs text-ink focus:border-accent focus:outline-none"
                  />
                </div>
              </>
            )}
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setMode('view')}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-ink-2 hover:bg-raised"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="approval-submit-modify-btn"
                onClick={handleConfirmModify}
                disabled={disabled}
                className="rounded-lg bg-accent px-3 py-1.5 font-medium text-xs text-on-accent hover:opacity-95 disabled:opacity-50"
              >
                Submit Modified
              </button>
            </div>
          </div>
        ) : mode === 'reject' ? (
          <div className="space-y-2 border border-danger/30 rounded-lg bg-danger-soft/20 p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-xs text-danger">Rejection Feedback</span>
              <span className="text-[11px] text-ink-3">Inject feedback into agent to re-plan</span>
            </div>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Explain why this action is rejected or propose alternate instructions..."
              rows={3}
              className="w-full rounded border border-line bg-sunken p-2.5 text-xs text-ink focus:border-danger focus:outline-none"
            />
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setMode('view')}
                className="rounded-lg border border-line px-3 py-1.5 text-xs text-ink-2 hover:bg-raised"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="approval-confirm-reject-btn"
                onClick={handleConfirmReject}
                disabled={disabled}
                className="rounded-lg bg-danger px-3 py-1.5 font-medium text-xs text-white hover:opacity-95 disabled:opacity-50"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-ink-3 uppercase text-[10px] tracking-wider">
                {isCommand ? 'Execution Plan' : 'Proposed Diff'}
              </span>
              <button
                type="button"
                onClick={() => setShowFullDiff(!showFullDiff)}
                className="flex items-center gap-1 text-[11px] text-ink-3 hover:text-ink font-mono"
              >
                {showFullDiff ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                <span>{showFullDiff ? 'Collapse' : 'Expand'}</span>
              </button>
            </div>
            {showFullDiff && (
              isCommand ? (
                <div
                  data-testid="command-viewer"
                  className="overflow-hidden rounded-lg border border-line bg-sunken font-mono text-xs shadow-sm"
                >
                  <div className="flex items-center justify-between border-b border-line/60 bg-raised/70 px-3 py-1.5 text-[11px] text-ink-3">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1 select-none">
                        <span className="h-2 w-2 rounded-full bg-danger/50" />
                        <span className="h-2 w-2 rounded-full bg-warn/50" />
                        <span className="h-2 w-2 rounded-full bg-ok/50" />
                      </div>
                      <span className="text-line-strong select-none">|</span>
                      <Terminal size={12} className="text-accent shrink-0" />
                      <span className="font-semibold text-ink-2">Terminal Shell</span>
                      <span className="text-ink-3/70 select-none">· workspace root</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopyCommand(initialCommand)}
                      data-testid="copy-command-btn"
                      className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono text-ink-3 hover:text-ink hover:bg-raised transition-colors border border-transparent hover:border-line"
                    >
                      {commandCopied ? (
                        <>
                          <Check size={11} className="text-ok" />
                          <span className="text-ok font-semibold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={11} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="p-3 bg-sunken/90 select-text">
                    <div className="flex items-start gap-2">
                      <span className="select-none font-bold text-accent">$</span>
                      <pre className="text-ok font-medium whitespace-pre-wrap break-all flex-1">{initialCommand}</pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div
                  data-testid="diff-viewer"
                  className="max-h-64 overflow-x-auto rounded-lg border border-line bg-sunken font-mono text-[11px] leading-relaxed select-text"
                >
                  <div className="min-w-full divide-y divide-line/20">
                    {parsedDiff.map((line, idx) => {
                      let rowStyle = 'text-ink-2';
                      if (line.type === 'add') {
                        rowStyle = 'bg-ok/15 text-ok';
                      } else if (line.type === 'delete') {
                        rowStyle = 'bg-danger/15 text-danger';
                      } else if (line.type === 'header') {
                        rowStyle = 'bg-accent/10 text-accent font-semibold';
                      } else if (line.type === 'meta') {
                        rowStyle = 'bg-raised/40 text-ink-3 italic';
                      }

                      return (
                        <div
                          key={idx}
                          className={cn('flex items-stretch hover:bg-surface/20 transition-colors', rowStyle)}
                        >
                          {/* Old line number */}
                          <span className="w-9 shrink-0 select-none px-2 py-0.5 text-right font-mono text-[10px] text-ink-3/60 border-r border-line/40">
                            {line.oldLineNumber ?? ''}
                          </span>
                          {/* New line number */}
                          <span className="w-9 shrink-0 select-none px-2 py-0.5 text-right font-mono text-[10px] text-ink-3/60 border-r border-line/40">
                            {line.newLineNumber ?? ''}
                          </span>
                          {/* Line content */}
                          <span className="flex-1 px-2 py-0.5 whitespace-pre overflow-x-visible">
                            {line.content}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {/* Action Controls */}
        {mode === 'view' && (
          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-line">
            <button
              type="button"
              data-testid="approval-reject-btn"
              onClick={() => setMode('reject')}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-raised px-3 py-1.5 font-medium text-xs text-danger hover:border-danger/40 hover:bg-danger-soft transition-colors disabled:opacity-50"
            >
              <X size={13} />
              <span>Reject with Feedback</span>
            </button>
            <button
              type="button"
              data-testid="approval-modify-btn"
              onClick={() => setMode('modify')}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-raised px-3 py-1.5 font-medium text-xs text-ink hover:border-line-strong hover:bg-surface transition-colors disabled:opacity-50"
            >
              <Edit3 size={13} />
              <span>{isCommand ? 'Modify Command' : 'Modify Diff'}</span>
            </button>
            <button
              type="button"
              data-testid="approval-approve-btn"
              onClick={handleApprove}
              disabled={disabled}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ok text-white px-3.5 py-1.5 font-medium text-xs hover:opacity-95 shadow-sm transition-opacity disabled:opacity-50"
            >
              <Check size={13} />
              <span>Approve & Run</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
