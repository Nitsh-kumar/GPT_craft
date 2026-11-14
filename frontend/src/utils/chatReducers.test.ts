import test from 'node:test';
import assert from 'node:assert/strict';
import type { ApprovalRequiredEnvelope, Message } from '../types/index.ts';
import {
  appendMessageChunk,
  applyAgentSseEvent,
  markAbortedActions,
  markMessageComplete,
  markMessageInterrupted,
} from './chatReducers.ts';

const baseAssistantMessage = (): Message => ({
  id: 'msg-1',
  role: 'assistant',
  content: '',
  timestamp: '2026-11-14T12:00:00.000Z',
  mode: 'agent',
  modelUsed: 'openai/gpt-oss-120b',
  modeUsed: 'agent',
  status: 'streaming',
  thoughts: [],
  actions: [],
});

test('applyAgentSseEvent updates thoughts, deduplicates action_call, and computes action_result status', () => {
  let msg = baseAssistantMessage();
  msg = applyAgentSseEvent(msg, { type: 'thought', thought: 'Inspecting files' });
  assert.deepEqual(msg.thoughts, ['Inspecting files']);

  msg = applyAgentSseEvent(
    msg,
    {
      type: 'action_call',
      actionId: 'act_1',
      tool: 'read_workspace_file',
      args: { path: 'README.md' },
      tier: 1,
    },
    { now: 1000 }
  );
  // Duplicate actionId should be ignored
  msg = applyAgentSseEvent(
    msg,
    {
      type: 'action_call',
      actionId: 'act_1',
      tool: 'read_workspace_file',
      args: { path: 'README.md' },
      tier: 1,
    },
    { now: 1050 }
  );
  assert.equal(msg.actions?.length, 1);
  assert.equal(msg.actions?.[0]?.status, 'running');

  msg = applyAgentSseEvent(
    msg,
    {
      type: 'action_result',
      actionId: 'act_1',
      tool: 'read_workspace_file',
      output: '1: # GPTCraft',
    },
    { now: 1045 }
  );
  assert.equal(msg.actions?.[0]?.status, 'completed');
  assert.equal(msg.actions?.[0]?.durationMs, 45);

  msg = applyAgentSseEvent(msg, {
    type: 'action_result',
    actionId: 'act_2',
    tool: 'run_terminal_command',
    output: 'Exit code: 1\nFailed',
    exitCode: 1,
  }, { defaultActionTier: 2 });
  assert.equal(msg.actions?.[1]?.tier, 2);
  assert.equal(msg.actions?.[1]?.status, 'failed');
});

test('appendMessageChunk, markMessageComplete, and markMessageInterrupted preserve approval on pre-stream failure', () => {
  const pendingApproval: ApprovalRequiredEnvelope = {
    actionId: 'act_hitl',
    tool: 'edit_workspace_file',
    tier: 2,
    parameters: { path: 'README.md', content: 'Updated' },
    rationale: 'Update docs',
  };

  let msg = baseAssistantMessage();
  msg = applyAgentSseEvent(msg, { type: 'approval_required', ...pendingApproval });
  assert.deepEqual(msg.approvalRequired, pendingApproval);

  // Pre-stream failure keeps approvalRequired intact and marks status interrupted
  const preStreamFailed = markMessageInterrupted(msg, { preserveApproval: pendingApproval });
  assert.equal(preStreamFailed.status, 'interrupted');
  assert.deepEqual(preStreamFailed.approvalRequired, pendingApproval);

  // Mid-stream failure after approval was cleared marks status interrupted without restoring approval
  const streamingMsg: Message = { ...preStreamFailed, approvalRequired: undefined, status: 'streaming' };
  const midStreamFailed = markMessageInterrupted(streamingMsg);
  assert.equal(midStreamFailed.status, 'interrupted');
  assert.equal(midStreamFailed.approvalRequired, undefined);

  const appended = appendMessageChunk(streamingMsg, 'Applied change.');
  assert.equal(appended.content, 'Applied change.');

  const completed = markMessageComplete(appended, { modelUsed: 'openai/gpt-oss-120b', modeUsed: 'agent' });
  assert.equal(completed.status, 'complete');
  assert.equal(completed.modelUsed, 'openai/gpt-oss-120b');
});

test('markAbortedActions marks unresolved assistant actions as aborted', () => {
  let msg = baseAssistantMessage();
  msg = applyAgentSseEvent(msg, {
    type: 'action_call',
    actionId: 'act_running',
    tool: 'run_terminal_command',
    args: { command: 'pytest' },
    tier: 2,
  });
  const aborted = markAbortedActions(msg);
  assert.equal(aborted.actions?.[0]?.status, 'aborted');
  assert.equal(aborted.actions?.[0]?.output, '[Execution aborted by user]');
});
