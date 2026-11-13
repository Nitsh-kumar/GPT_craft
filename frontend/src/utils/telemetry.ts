import type { AgentActionTelemetry } from '../types/index.ts';

export interface ParsedDiffLine {
  type: 'add' | 'delete' | 'context' | 'header' | 'meta';
  content: string;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export function formatLatency(durationMs?: number): string {
  if (durationMs === undefined || durationMs === null || isNaN(durationMs)) {
    return '';
  }
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ms`;
  }
  return `${(durationMs / 1000).toFixed(1)}s`;
}

export function getToolTierMeta(tier: number): {
  label: string;
  shortLabel: string;
  badgeClass: string;
  isMutation: boolean;
} {
  if (tier >= 2) {
    return {
      label: 'Tier 2 · Workspace Mutation',
      shortLabel: 'Tier 2 Mutation',
      badgeClass: 'border-warn/30 bg-warn/15 text-warn',
      isMutation: true,
    };
  }
  return {
    label: 'Tier 1 · Read-Only',
    shortLabel: 'Tier 1 Read-Only',
    badgeClass: 'border-accent/30 bg-accent/10 text-accent',
    isMutation: false,
  };
}

export function detectActionStatus(action: AgentActionTelemetry): {
  status: 'running' | 'completed' | 'failed' | 'aborted';
  exitCode?: number;
  isError: boolean;
  statusLabel: string;
} {
  if (action.status === 'aborted' || action.output === '[Execution aborted by user]') {
    return {
      status: 'aborted',
      isError: true,
      statusLabel: 'Aborted',
    };
  }

  if (action.output === undefined) {
    return {
      status: 'running',
      isError: false,
      statusLabel: 'Running...',
    };
  }

  // Look for exit code explicitly or in output text (e.g. "Exit code: 1")
  let exitCode = action.exitCode;
  if (exitCode === undefined) {
    const match = action.output.match(/Exit code:\s*(-?\d+)/i);
    if (match) {
      exitCode = parseInt(match[1], 10);
    }
  }

  const outputLower = action.output.toLowerCase();
  const hasErrorIndicator =
    (exitCode !== undefined && exitCode !== 0) ||
    outputLower.startsWith('error:') ||
    outputLower.includes('error executing command') ||
    outputLower.includes('traceback (most recent call last)');

  if (hasErrorIndicator) {
    return {
      status: 'failed',
      exitCode,
      isError: true,
      statusLabel: exitCode !== undefined ? `Exit ${exitCode}` : 'Failed',
    };
  }

  return {
    status: 'completed',
    exitCode: exitCode ?? 0,
    isError: false,
    statusLabel: exitCode !== undefined ? `Exit ${exitCode}` : 'Completed',
  };
}

export function parseUnifiedDiff(rawDiff?: string): ParsedDiffLine[] {
  if (!rawDiff || !rawDiff.trim()) {
    return [
      {
        type: 'meta',
        content: '(No diff available)',
      },
    ];
  }

  const lines = rawDiff.split(/\r?\n/);
  const parsed: ParsedDiffLine[] = [];

  let currentOldLine = 1;
  let currentNewLine = 1;
  let hasHunkHeader = false;

  for (const line of lines) {
    if (line.startsWith('@@')) {
      hasHunkHeader = true;
      const match = line.match(/^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@/);
      if (match) {
        currentOldLine = parseInt(match[1], 10);
        currentNewLine = parseInt(match[2], 10);
      }
      parsed.push({
        type: 'header',
        content: line,
      });
    } else if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('diff ') || line.startsWith('index ')) {
      parsed.push({
        type: 'meta',
        content: line,
      });
    } else if (line.startsWith('+')) {
      parsed.push({
        type: 'add',
        content: line,
        newLineNumber: currentNewLine++,
      });
    } else if (line.startsWith('-')) {
      parsed.push({
        type: 'delete',
        content: line,
        oldLineNumber: currentOldLine++,
      });
    } else {
      // Context line
      parsed.push({
        type: 'context',
        content: line,
        oldLineNumber: hasHunkHeader ? currentOldLine++ : undefined,
        newLineNumber: hasHunkHeader ? currentNewLine++ : undefined,
      });
    }
  }

  return parsed;
}
