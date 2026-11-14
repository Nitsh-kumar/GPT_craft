import type {
  AgentActionTelemetry,
  ApprovalRequiredEnvelope,
  CraftMode,
  Message,
  SseEventEnvelope,
} from '../types/index.ts';

function isActionResultError(output: string, exitCode?: number): boolean {
  return (
    (exitCode !== undefined && exitCode !== 0) ||
    output.startsWith('Error:') ||
    output.includes('Traceback (most recent call last)')
  );
}

export function appendMessageChunk(msg: Message, chunk: string): Message {
  return { ...msg, content: (msg.content || '') + chunk };
}

export function applyAgentSseEvent(
  msg: Message,
  event: SseEventEnvelope,
  options: { now?: number; defaultActionTier?: number } = {}
): Message {
  const now = options.now ?? Date.now();
  if (event.type === 'thought') {
    return { ...msg, thoughts: [...(msg.thoughts || []), event.thought] };
  }
  if (event.type === 'action_call') {
    const currentActions = msg.actions || [];
    if (currentActions.some((a) => a.actionId === event.actionId)) {
      return msg;
    }
    const newAction: AgentActionTelemetry = {
      actionId: event.actionId,
      tool: event.tool,
      args: event.args,
      tier: event.tier,
      startTime: now,
      status: 'running',
    };
    return { ...msg, actions: [...currentActions, newAction] };
  }
  if (event.type === 'action_result') {
    const currentActions = msg.actions || [];
    const idx = currentActions.findIndex((a) => a.actionId === event.actionId);
    const isError = isActionResultError(event.output, event.exitCode);
    const resolvedStatus =
      (event.status as AgentActionTelemetry['status']) || (isError ? 'failed' : 'completed');

    if (idx >= 0) {
      const updated = [...currentActions];
      const existing = updated[idx];
      const calculatedDuration =
        existing.startTime !== undefined ? Math.max(1, now - existing.startTime) : undefined;
      updated[idx] = {
        ...existing,
        output: event.output,
        durationMs: event.durationMs ?? calculatedDuration,
        exitCode: event.exitCode,
        status: resolvedStatus,
      };
      return { ...msg, actions: updated };
    }

    const fallbackTier =
      msg.approvalRequired?.actionId === event.actionId
        ? msg.approvalRequired.tier
        : (options.defaultActionTier ?? 1);
    return {
      ...msg,
      actions: [
        ...currentActions,
        {
          actionId: event.actionId,
          tool: event.tool,
          args: {},
          tier: fallbackTier,
          output: event.output,
          durationMs: event.durationMs,
          exitCode: event.exitCode,
          status: resolvedStatus,
        },
      ],
    };
  }
  if (event.type === 'approval_required') {
    return {
      ...msg,
      approvalRequired: {
        actionId: event.actionId,
        tool: event.tool,
        tier: event.tier,
        parameters: event.parameters,
        rationale: event.rationale,
        ...(event.diff !== undefined ? { diff: event.diff } : {}),
      },
    };
  }
  return msg;
}

export function markMessageComplete(
  msg: Message,
  result: { modelUsed?: string; modeUsed?: CraftMode }
): Message {
  return {
    ...msg,
    status: 'complete',
    modelUsed: result.modelUsed ?? msg.modelUsed,
    modeUsed: result.modeUsed ?? msg.modeUsed,
  };
}

export function markMessageInterrupted(
  msg: Message,
  options?: { preserveApproval?: ApprovalRequiredEnvelope }
): Message {
  return {
    ...msg,
    status: 'interrupted',
    ...(options?.preserveApproval ? { approvalRequired: options.preserveApproval } : {}),
  };
}

export function markAbortedActions(msg: Message): Message {
  if (msg.role !== 'assistant' || !msg.actions) return msg;
  const updatedActions = msg.actions.map((action) =>
    action.output === undefined
      ? {
          ...action,
          output: '[Execution aborted by user]',
          status: 'aborted' as const,
        }
      : action
  );
  return { ...msg, actions: updatedActions };
}
