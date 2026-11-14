import { test, expect } from '@playwright/test';

// Isolated UI contract checks: no account creation, live auth, or model calls.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('accessToken', 'offline-test-token'));
  await page.route('**/auth/me?**', route => route.fulfill({ json: { id:1, name:'Test User', email:'test@example.com', plan:'free' } }));
  await page.route('**/chat/models', route => route.fulfill({ json: [
    { id:'openai/gpt-oss-20b', name:'GPT-OSS 20B', description:'Test provider', requiredPlan:'free' },
  ] }));
  await page.route('**/chat/quota', route => route.fulfill({ json: { requestsRemaining:50, tokensRemaining:5000, totalRequests:50, totalTokens:5000 } }));
  await page.route('**/chat/conversations', route => route.fulfill({ json: [] }));
  await page.route('https://offline.invalid/**', route => route.abort());
});

test('chat shows the resolved model and explicit completion', async ({ page }) => {
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'data: {"type":"start","conversation_id":1,"model_used":"openai/gpt-oss-20b","mode_used":"standard"}\n\n' +
    'data: {"type":"chunk","content":"Offline test response"}\n\n' +
    'data: {"type":"done","conversation_id":1,"model_used":"openai/gpt-oss-20b","mode_used":"standard","tokens_used":42,"tokens_remaining":4958}\n\n'
  }));
  await page.goto('/chat');
  await expect(page.getByRole('complementary').getByTestId('sidebar-user-name')).toHaveText('Test User');
  await page.getByTestId('chat-input').fill('Hello');
  await page.getByTestId('send-button').click();
  await expect(page.getByText('Offline test response')).toBeVisible();
  await expect(page.getByTestId('send-button')).toBeVisible();
  await expect(page.getByText('openai/gpt-oss-20b', { exact:true })).toBeVisible();
});

test('premature EOF displays an error and marks partial text incomplete', async ({ page }) => {
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'data: {"type":"chunk","content":"Partial response"}\n\n'
  }));
  await page.goto('/chat');
  await page.getByTestId('chat-input').fill('Hello');
  await page.getByTestId('send-button').click();
  await expect(page.getByTestId('chat-error-banner')).toContainText('interrupted');
  await expect(page.getByText('Generation interrupted — this response is incomplete.')).toBeVisible();
});

test('subscription controls cannot grant paid entitlements', async ({ page }) => {
  await page.goto('/subscription');
  await expect(page.getByTestId('plan-card-free')).toContainText('All 5 Craft Modes');
  await expect(page.getByTestId('select-plan-super')).toBeDisabled();
  await expect(page.getByTestId('select-plan-hyper')).toBeDisabled();
  await expect(page.getByText('Paid plan changes are not available yet.', { exact:false })).toBeVisible();
});

test('agent studio displays telemetry drawer, diff inspector, and resumes after approval', async ({ page }) => {
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'event: thought\ndata: {"thought":"Inspecting README before editing"}\n\n' +
    'event: action_call\ndata: {"actionId":"act_1","tool":"read_workspace_file","args":{"path":"README.md"},"tier":1}\n\n' +
    'event: action_result\ndata: {"actionId":"act_1","tool":"read_workspace_file","output":"1: # GPTCraft","durationMs":45,"exitCode":0}\n\n' +
    'event: approval_required\ndata: {"actionId":"act_2","tool":"edit_workspace_file","tier":2,"parameters":{"path":"README.md","content":"# GPTCraft\\nUpdated"},"rationale":"Add tagline to README","diff":"--- a/README.md\\n+++ b/README.md\\n@@ -1,1 +1,2 @@\\n # GPTCraft\\n+Updated"}\n\n' +
    'event: done\ndata: {"status":"awaiting_approval","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent"}\n\n'
  }));

  await page.route('**/chat/approval', async route => {
    const body = route.request().postDataJSON() as { actionId: string; decision: string };
    expect(body.actionId).toBe('act_2');
    expect(body.decision).toBe('approve');
    await route.fulfill({ contentType:'text/event-stream', body:
      'event: action_result\ndata: {"actionId":"act_2","tool":"edit_workspace_file","output":"Updated README.md"}\n\n' +
      'event: token\ndata: {"token":"Applied your approved update to README.md."}\n\n' +
      'event: done\ndata: {"status":"completed","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent","tokensUsed":85,"tokensRemaining":4915}\n\n'
    });
  });

  await page.goto('/chat');
  await page.getByTestId('craft-mode-agent').click();
  await page.getByTestId('chat-input').fill('Update README.md with a tagline');
  await page.getByTestId('send-button').click();

  await expect(page.getByTestId('telemetry-drawer')).toBeVisible();
  await expect(page.getByTestId('telemetry-actions-count')).toContainText('1 tool call');
  await expect(page.getByTestId('telemetry-thoughts-count')).toContainText('1 thought');
  await expect(page.getByTestId('telemetry-total-latency')).toContainText('45ms');

  await expect(page.getByTestId('approval-card')).toBeVisible();
  await expect(page.getByTestId('diff-viewer')).toContainText('+Updated');

  await page.getByTestId('approval-approve-btn').click();
  await expect(page.getByText('Applied your approved update to README.md.')).toBeVisible();
  await expect(page.getByTestId('approval-card')).toBeHidden();
});

test('pre-stream approval failure preserves approval card and allows retry', async ({ page }) => {
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'event: approval_required\ndata: {"actionId":"act_retry","tool":"edit_workspace_file","tier":2,"parameters":{"path":"README.md","content":"Retry"},"rationale":"Retry update","diff":"--- a/README.md\\n+++ b/README.md\\n@@ -1,1 +1,2 @@\\n # GPTCraft\\n+Retry"}\n\n' +
    'event: done\ndata: {"status":"interrupted","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent"}\n\n'
  }));

  let attempts = 0;
  await page.route('**/chat/approval', async route => {
    attempts += 1;
    if (attempts === 1) {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Temporary approval error' }) });
      return;
    }
    await route.fulfill({ contentType:'text/event-stream', body:
      'event: action_result\ndata: {"actionId":"act_retry","tool":"edit_workspace_file","output":"Updated README.md"}\n\n' +
      'event: token\ndata: {"token":"Recovered after retry."}\n\n' +
      'event: done\ndata: {"status":"completed","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent","tokensUsed":55,"tokensRemaining":4945}\n\n'
    });
  });

  await page.goto('/chat');
  await page.getByTestId('craft-mode-agent').click();
  await page.getByTestId('chat-input').fill('Update README.md');
  await page.getByTestId('send-button').click();

  await expect(page.getByTestId('approval-card')).toBeVisible();
  await page.getByTestId('approval-approve-btn').click();

  await expect(page.getByTestId('chat-error-banner')).toContainText('Temporary approval error');
  await expect(page.getByText('Generation interrupted — this response is incomplete.')).toBeVisible();
  await expect(page.getByTestId('approval-card')).toBeVisible();

  await page.getByTestId('approval-approve-btn').click();
  await expect(page.getByText('Recovered after retry.')).toBeVisible();
  await expect(page.getByTestId('approval-card')).toBeHidden();
});

test('approval premature EOF marks response interrupted and 401 triggers unauthorized logout', async ({ page }) => {
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'event: approval_required\ndata: {"actionId":"act_eof","tool":"edit_workspace_file","tier":2,"parameters":{"path":"README.md","content":"EOF"},"rationale":"Test EOF"}\n\n' +
    'event: done\ndata: {"status":"interrupted","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent"}\n\n'
  }));

  await page.route('**/chat/approval', route => route.fulfill({ contentType:'text/event-stream', body:
    'event: token\ndata: {"token":"Partial approval output"}\n\n'
  }));

  await page.goto('/chat');
  await page.getByTestId('craft-mode-agent').click();
  await page.getByTestId('chat-input').fill('Test EOF on approval');
  await page.getByTestId('send-button').click();

  await expect(page.getByTestId('approval-card')).toBeVisible();
  await page.getByTestId('approval-approve-btn').click();

  await expect(page.getByTestId('chat-error-banner')).toContainText('interrupted');
  await expect(page.getByText('Generation interrupted — this response is incomplete.')).toBeVisible();

  // Now verify 401 on approval dispatches auth:unauthorized and redirects to /login
  await page.route('**/chat/stream', route => route.fulfill({ contentType:'text/event-stream', body:
    'event: approval_required\ndata: {"actionId":"act_401","tool":"edit_workspace_file","tier":2,"parameters":{"path":"README.md","content":"401"},"rationale":"Test 401"}\n\n' +
    'event: done\ndata: {"status":"interrupted","conversationId":"1","modelUsed":"openai/gpt-oss-20b","modeUsed":"agent"}\n\n'
  }));
  await page.route('**/chat/approval', route => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Token expired' }),
  }));

  await page.goto('/chat');
  await page.getByTestId('craft-mode-agent').click();
  await page.getByTestId('chat-input').fill('Test 401 on approval');
  await page.getByTestId('send-button').click();

  await expect(page.getByTestId('approval-card')).toBeVisible();
  await page.getByTestId('approval-approve-btn').click();
  await page.waitForURL('**/login');
});
