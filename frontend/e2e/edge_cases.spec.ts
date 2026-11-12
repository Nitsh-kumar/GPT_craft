import { test, expect } from '@playwright/test';

test.describe('GPTCraft Edge Cases, Error Handling & System Controls', () => {
  test('1. Invalid credentials display error alert', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[placeholder="you@example.com"]', 'nonexistent_user@example.com');
    await page.fill('input[placeholder="••••••••"]', 'WrongPass!');
    await page.click('button[type="submit"]');

    // Error banner should be visible with appropriate message
    const errorBanner = page.locator('div.text-danger');
    await expect(errorBanner).toBeVisible({ timeout: 5000 });
    await expect(errorBanner).toContainText('Invalid login credentials');
  });

  test('2. Registration with duplicate email displays error alert', async ({ page }) => {
    const uniqueEmail = `dup_test_${Date.now()}@gptcraft.dev`;
    const password = 'CorrectPassword123!';

    // 1. First register the user
    await page.goto('/register');
    await page.fill('input[placeholder="John Doe"]', 'Edge Tester');
    await page.fill('input[placeholder="you@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="••••••••"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    // 2. Logout
    await page.getByTestId('logout-button').first().click();
    await page.waitForURL('**/login');

    // 3. Try to register the same email again
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

    // Click light theme
    await page.getByTestId('theme-light').click();
    await expect(html).not.toHaveClass(/dark/);

    // Click dark theme
    await page.getByTestId('theme-dark').click();
    await expect(html).toHaveClass(/dark/);
  });

  test('4. Empty input disables send button & conversation deletion', async ({ page }) => {
    const userEmail = `del_test_${Date.now()}@gptcraft.dev`;
    const password = 'CorrectPassword123!';

    // Register a fresh user
    await page.goto('/register');
    await page.fill('input[placeholder="John Doe"]', 'Delete Tester');
    await page.fill('input[placeholder="you@example.com"]', userEmail);
    await page.fill('input[placeholder="••••••••"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    // Send button should be disabled when empty
    const sendButton = page.getByTestId('send-button');
    await expect(sendButton).toBeDisabled();

    // Type spaces only - should remain disabled
    const chatInput = page.getByTestId('chat-input');
    await chatInput.fill('    ');
    await expect(sendButton).toBeDisabled();

    // Send a real message to create a conversation
    await chatInput.fill('Testing conversation deletion flow.');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    // Wait for the response stream to complete
    await expect(page.locator('.prose-craft').last()).toBeVisible({ timeout: 20000 });

    // Verify conversation appeared in sidebar
    const convItem = page.locator('[data-testid^="conversation-item-"]').first();
    await expect(convItem).toBeVisible();

    // Delete conversation via trash button
    const deleteButton = page.locator('button[aria-label^="Delete"]').first();
    await deleteButton.click({ force: true });

    // Wait for delete to take effect
    await page.waitForTimeout(500);

    // Now clicking New Conversation resets to Studio Workbench
    const newChatButton = page.getByTestId('new-conversation-button').first();
    await newChatButton.click();
    await expect(page.locator('h1')).toContainText('Studio Workbench');
  });
});
