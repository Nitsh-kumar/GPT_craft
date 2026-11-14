import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatLatency,
  getToolTierMeta,
  detectActionStatus,
  parseUnifiedDiff,
} from './telemetry.ts';

test('formatLatency formats milliseconds and seconds consistently', () => {
  assert.equal(formatLatency(undefined), '');
  assert.equal(formatLatency(Number.NaN), '');
  assert.equal(formatLatency(42), '42ms');
  assert.equal(formatLatency(999), '999ms');
  assert.equal(formatLatency(1500), '1.5s');
});

test('getToolTierMeta distinguishes Tier 1 read-only from Tier 2 mutation', () => {
  assert.equal(getToolTierMeta(1).isMutation, false);
  assert.equal(getToolTierMeta(1).shortLabel, 'Tier 1 Read-Only');
  assert.equal(getToolTierMeta(2).isMutation, true);
  assert.equal(getToolTierMeta(2).shortLabel, 'Tier 2 Mutation');
});

test('detectActionStatus derives running, completed, failed, and aborted states', () => {
  const running = detectActionStatus({
    actionId: 'a1',
    tool: 'read_workspace_file',
    args: {},
    tier: 1,
  });
  assert.equal(running.status, 'running');
  assert.equal(running.statusLabel, 'Running...');

  const aborted = detectActionStatus({
    actionId: 'a2',
    tool: 'edit_workspace_file',
    args: {},
    tier: 2,
    status: 'aborted',
  });
  assert.equal(aborted.status, 'aborted');
  assert.equal(aborted.isError, true);

  const failedExit = detectActionStatus({
    actionId: 'a3',
    tool: 'run_terminal_command',
    args: {},
    tier: 2,
    output: 'Exit code: 2\nSTDERR:\ncommand failed',
  });
  assert.equal(failedExit.status, 'failed');
  assert.equal(failedExit.exitCode, 2);
  assert.equal(failedExit.statusLabel, 'Exit 2');

  const ok = detectActionStatus({
    actionId: 'a4',
    tool: 'read_workspace_file',
    args: {},
    tier: 1,
    output: '1: hello',
  });
  assert.equal(ok.status, 'completed');
  assert.equal(ok.isError, false);
});

test('parseUnifiedDiff tracks old and new line numbers across hunks', () => {
  const empty = parseUnifiedDiff('');
  assert.deepEqual(empty, [{ type: 'meta', content: '(No diff available)' }]);

  const diff = [
    '--- a/app.py',
    '+++ b/app.py',
    '@@ -10,3 +10,3 @@',
    ' context',
    '-old line',
    '+new line',
  ].join('\n');

  const lines = parseUnifiedDiff(diff);
  assert.equal(lines[0]?.type, 'meta');
  assert.equal(lines[1]?.type, 'meta');
  assert.equal(lines[2]?.type, 'header');
  assert.deepEqual(lines[3], {
    type: 'context',
    content: ' context',
    oldLineNumber: 10,
    newLineNumber: 10,
  });
  assert.deepEqual(lines[4], {
    type: 'delete',
    content: '-old line',
    oldLineNumber: 11,
  });
  assert.deepEqual(lines[5], {
    type: 'add',
    content: '+new line',
    newLineNumber: 11,
  });
});
