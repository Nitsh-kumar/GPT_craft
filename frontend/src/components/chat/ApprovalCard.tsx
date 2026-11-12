import React, { useState } from 'react';
import { ShieldAlert, Check, X, Edit3, FileCode, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { ApprovalRequiredEnvelope } from '../../types';
import { cn } from '../../utils/cn';

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
  const [mode, setMode] = useState<'view' | 'modify' | 'reject'>('view');
  const [modifiedPath, setModifiedPath] = useState(String(approval.parameters.path || ''));
  const [modifiedContent, setModifiedContent] = useState(String(approval.parameters.content || ''));
  const [feedback, setFeedback] = useState('');
  const [showFullDiff, setShowFullDiff] = useState(true);

  const diffLines = (approval.diff || '(No diff available)').split('\n');

  const handleApprove = () => {
    onDecision(approval.actionId, 'approve');
  };

  const handleConfirmModify = () => {
    onDecision(
      approval.actionId,
      'modify',
      {
        path: modifiedPath,
        content: modifiedContent,
        mode: approval.parameters.mode || 'write',
      }
    );
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
            {approval.rationale || 'Mutating workspace file'}
          </p>
        </div>

        {/* Target Path */}
        <div className="flex items-center gap-2 font-mono text-xs bg-sunken/60 px-3 py-1.5 rounded-lg border border-line">
          <FileCode size={13} className="text-accent shrink-0" />
          <span className="text-ink-3">Target:</span>
          <span className="text-ink font-medium truncate">{String(approval.parameters.path || 'Unknown')}</span>
        </div>

        {/* Diff Preview / Modification Editor */}
        {mode === 'modify' ? (
          <div className="space-y-2 border border-line rounded-lg bg-raised p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold text-xs text-accent">Modify Target Content</span>
              <span className="text-[11px] text-ink-3">Edit file content below</span>
            </div>
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
                Proposed Diff
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
              <div
                data-testid="diff-viewer"
                className="max-h-60 overflow-x-auto rounded-lg border border-line bg-sunken p-2.5 font-mono text-[11px] leading-relaxed"
              >
                {diffLines.map((line, idx) => {
                  let lineStyle = 'text-ink-2';
                  if (line.startsWith('+') && !line.startsWith('+++')) {
                    lineStyle = 'bg-ok/15 text-ok font-semibold';
                  } else if (line.startsWith('-') && !line.startsWith('---')) {
                    lineStyle = 'bg-danger/15 text-danger font-semibold';
                  } else if (line.startsWith('@@')) {
                    lineStyle = 'text-accent font-semibold';
                  }
                  return (
                    <div key={idx} className={cn('px-1.5 py-0.5 rounded-sm whitespace-pre', lineStyle)}>
                      {line}
                    </div>
                  );
                })}
              </div>
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
              <span>Modify Diff</span>
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
