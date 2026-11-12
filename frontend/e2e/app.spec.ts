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
  await expect(page.getByTestId('select-plan-super')).toBeDisabled();
  await expect(page.getByTestId('select-plan-hyper')).toBeDisabled();
  await expect(page.getByText('Paid plan changes are not available yet.', { exact:false })).toBeVisible();
});
