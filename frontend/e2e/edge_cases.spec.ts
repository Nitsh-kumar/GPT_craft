import { test, expect } from '@playwright/test';

// Isolated UI edge-case contracts using mocked API routes (no live backend required).
test.describe('GPTCraft Edge Cases, Error Handling & System Controls', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('https://offline.invalid/**', (route) => route.abort());
    await page.route('**/chat/models', (route) =>
      route.fulfill({
        json: [
          {
            id: 'openai/gpt-oss-20b',
            name: 'GPT-OSS 20B',
            description: 'Test provider',
            requiredPlan: 'free',
          },
        ],
      })
    );
    await page.route('**/chat/quota', (route) =>
      route.fulfill({
        json: {
          requestsRemaining: 50,
          tokensRemaining: 5000,
          totalRequests: 50,
          totalTokens: 5000,
        },
      })
    );
  });

  test('1. Invalid credentials display error alert', async ({ page }) => {
    await page.route('https://offline.invalid/auth/v1/token**', (route) =>
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'invalid_grant',
          error_description: 'Invalid login credentials',
        }),
      })
    );

    await page.goto('/login');
    await page.fill('input[placeholder="you@example.com"]', 'nonexistent_user@example.com');
    await page.fill('input[placeholder="••••••••"]', 'WrongPass!');
    await page.click('button[type="submit"]');

    const errorBanner = page.locator('div.text-danger');
    await expect(errorBanner).toBeVisible({ timeout: 5000 });
    await expect(errorBanner).toContainText('Invalid login credentials');
  });

  test('2. Registration with duplicate email displays error alert', async ({ page }) => {
    let registered = false;
    const uniqueEmail = `dup_test_${Date.now()}@gptcraft.dev`;
    const password = 'CorrectPassword123!';

    await page.route('https://offline.invalid/auth/v1/signup**', (route) => {
      if (!registered) {
        registered = true;
        const mockUser = {
          id: 'user-1',
          aud: 'authenticated',
          role: 'authenticated',
          email: uniqueEmail,
          identities: [{ id: 'identity-1', user_id: 'user-1', provider: 'email' }],
        };
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: 'offline-test-token',
            token_type: 'bearer',
            expires_in: 3600,
            refresh_token: 'offline-refresh-token',
            user: mockUser,
            session: {
              access_token: 'offline-test-token',
              token_type: 'bearer',
              expires_in: 3600,
              refresh_token: 'offline-refresh-token',
              user: mockUser,
            },
          }),
        });
      }
      return route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 'user_already_exists',
          msg: 'Email already registered',
        }),
      });
    });
    await page.route('https://offline.invalid/auth/v1/logout**', (route) =>
      route.fulfill({ status: 204, body: '' })
    );
    await page.route('**/auth/me?**', (route) =>
      route.fulfill({ json: { id: 1, name: 'Edge Tester', email: uniqueEmail, plan: 'free' } })
    );
    await page.route('**/chat/conversations', (route) => route.fulfill({ json: [] }));

    await page.goto('/register');
    await page.fill('input[placeholder="John Doe"]', 'Edge Tester');
    await page.fill('input[placeholder="you@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="••••••••"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    await page.getByTestId('logout-button').first().click();
    await page.waitForURL('**/login');

    await page.goto('/register');
    await page.fill('input[placeholder="John Doe"]', 'Duplicate Tester');
    await page.fill('input[placeholder="you@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="••••••••"]', password);
    await page.click('button[type="submit"]');

    const errorBanner = page.locator('div.text-danger');
    await expect(errorBanner).toBeVisible({ timeout: 5000 });
    await expect(errorBanner).toContainText('Email already registered');
  });

  test('3. Theme Switcher toggles dark / light class on html element', async ({ page }) => {
    await page.goto('/login');
    const html = page.locator('html');

    await page.getByTestId('theme-light').click();
    await expect(html).not.toHaveClass(/dark/);

    await page.getByTestId('theme-dark').click();
    await expect(html).toHaveClass(/dark/);
  });

  test('4. Empty input disables send button & conversation deletion', async ({ page }) => {
    const now = new Date().toISOString();
    let conversations: Array<{ id: number; title: string; created_at: string; updated_at: string }> = [];

    await page.addInitScript(() => localStorage.setItem('accessToken', 'offline-test-token'));
    await page.route('**/auth/me?**', (route) =>
      route.fulfill({ json: { id: 1, name: 'Delete Tester', email: 'del@gptcraft.dev', plan: 'free' } })
    );
    await page.route('**/chat/conversations', (route) => route.fulfill({ json: conversations }));
    await page.route('**/chat/stream', (route) => {
      conversations = [
        {
          id: 101,
          title: 'Testing conversation deletion...',
          created_at: now,
          updated_at: now,
        },
      ];
      return route.fulfill({
        contentType: 'text/event-stream',
        body:
          'data: {"type":"start","conversation_id":101,"model_used":"openai/gpt-oss-20b","mode_used":"standard"}\n\n' +
          'data: {"type":"chunk","content":"Conversation created for deletion test."}\n\n' +
          'data: {"type":"done","conversation_id":101,"model_used":"openai/gpt-oss-20b","mode_used":"standard","tokens_used":25,"tokens_remaining":4975}\n\n',
      });
    });
    await page.route('**/chat/101', (route) => {
      if (route.request().method() === 'DELETE') {
        conversations = [];
        return route.fulfill({ status: 204, body: '' });
      }
      return route.continue();
    });

    await page.goto('/chat');

    const sendButton = page.getByTestId('send-button');
    await expect(sendButton).toBeDisabled();

    const chatInput = page.getByTestId('chat-input');
    await chatInput.fill('    ');
    await expect(sendButton).toBeDisabled();

    await chatInput.fill('Testing conversation deletion flow.');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    await expect(page.getByText('Conversation created for deletion test.')).toBeVisible();

    const convItem = page.locator('[data-testid^="conversation-item-"]').first();
    await expect(convItem).toBeVisible();

    const deleteButton = page.locator('button[aria-label^="Delete"]').first();
    await deleteButton.click({ force: true });
    await expect(convItem).toHaveCount(0);

    const newChatButton = page.getByTestId('new-conversation-button').first();
    await newChatButton.click();
    await expect(page.locator('h1')).toContainText('Studio Workbench');
  });
});
