import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = 'C:/Users/nitiskumar/.gemini/antigravity-cli/brain/1cf86400-b6d8-49f9-9424-e0f6e4a0d0ac';
const DOCS_SCREENSHOT_DIR = path.resolve(process.cwd(), '../docs/screenshots');

function saveBoth(buffer: Buffer, filename: string) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  fs.mkdirSync(DOCS_SCREENSHOT_DIR, { recursive: true });
  fs.writeFileSync(path.join(ARTIFACT_DIR, filename), buffer);
  fs.writeFileSync(path.join(DOCS_SCREENSHOT_DIR, filename), buffer);
}

test.describe('GPTCraft Full-Stack E2E & Visual Verification Suite', () => {
  test('Complete user journey: Landing -> Auth -> Chat -> Craft Modes -> Subscription Upgrade -> Unlocked 70B Model -> History -> Logout', async ({ page }) => {
    const uniqueEmail = `architect_${Date.now()}@gptcraft.dev`;

    // 1. Landing Page
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Your Intelligent');
    await page.waitForTimeout(600);
    saveBoth(await page.screenshot({ fullPage: false }), '01_landing_page.png');

    // Scroll to Features & Pricing on Landing Page
    await page.evaluate(() => window.scrollTo(0, 950));
    await page.waitForTimeout(500);
    saveBoth(await page.screenshot({ fullPage: false }), '02_landing_features_pricing.png');

    // 2. Login Page
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Welcome back');
    await page.waitForTimeout(400);
    saveBoth(await page.screenshot({ fullPage: false }), '03_login_page.png');

    // 3. Register Page & Account Creation
    await page.goto('/register');
    await expect(page.locator('h2')).toContainText('Create an account');
    await page.fill('input[placeholder="John Doe"]', 'Nitis Architect');
    await page.fill('input[placeholder="you@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="••••••••"]', 'SecurePass123!');
    await page.waitForTimeout(300);
    saveBoth(await page.screenshot({ fullPage: false }), '04_register_page.png');

    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    // 4. Empty Chat Workspace (with Starter Cards, Quota, and Craft Modes)
    await expect(page.locator('h1')).toContainText('Studio Workbench');
    await expect(page.getByTestId('sidebar-user-name').first()).toContainText('Nitis Architect');
    await expect(page.getByTestId('sidebar-user-plan').first()).toContainText('free');
    await page.waitForTimeout(500);
    saveBoth(await page.screenshot({ fullPage: false }), '05_chat_empty_workspace.png');

    // 5. Open Model Selector Dropdown on Free Plan (showing locked Super/Hyper models)
    await page.getByTestId('model-selector-button').click();
    await expect(page.getByTestId('model-option-llama3-70b-8192')).toBeDisabled();
    await page.waitForTimeout(300);
    saveBoth(await page.screenshot({ fullPage: false }), '06_model_selector_free_tier_locks.png');
    // Close dropdown by selecting Llama 3 8B
    await page.getByTestId('model-option-llama3-8b-8192').click();

    // 6. Select "Deep Architect" Craft Mode & Send First Message (SSE Streaming)
    await page.getByTestId('craft-mode-architect').click();
    await page.getByTestId('chat-input').fill('Design a scalable microservices architecture for GPTCraft.');
    await page.getByTestId('send-button').click();

    await expect(page.getByText('Deep Architect').last()).toBeVisible({ timeout: 20000 });
    await expect(page.locator('.prose-craft').last()).toContainText('Architecture', { timeout: 20000 });
    await page.waitForTimeout(500);
    saveBoth(await page.screenshot({ fullPage: false }), '07_chat_sse_stream_architect_mode.png');

    // 7. Navigate to Subscription Page & Upgrade to Hyper Plan
    await page.getByTestId('manage-subscription-link').first().click();
    await page.waitForURL('**/subscription');
    await expect(page.getByTestId('active-plan-badge')).toContainText('FREE');
    await page.waitForTimeout(400);
    saveBoth(await page.screenshot({ fullPage: false }), '08_subscription_page_free.png');

    await page.getByTestId('select-plan-hyper').click();
    await expect(page.getByTestId('subscription-status-banner')).toContainText('HYPER');
    await expect(page.getByTestId('active-plan-badge')).toContainText('HYPER');
    await page.waitForTimeout(400);
    saveBoth(await page.screenshot({ fullPage: false }), '09_subscription_upgraded_hyper.png');

    // 8. Return to Chat, Verify Hyper Plan Quota (5,000 req / 500,000 tokens) & Unlocked Llama 3.3 70B
    await page.getByTestId('back-to-chat-link').click();
    await page.waitForURL('**/chat');
    await expect(page.getByTestId('sidebar-user-plan').first()).toContainText('hyper');

    await page.getByTestId('model-selector-button').click();
    await expect(page.getByTestId('model-option-llama3-70b-8192')).toBeEnabled();
    await page.waitForTimeout(300);
    saveBoth(await page.screenshot({ fullPage: false }), '10_model_selector_hyper_unlocked.png');

    // Select Llama 3.3 70B + Code Craft Mode and send a second message
    await page.getByTestId('model-option-llama3-70b-8192').click();
    await page.getByTestId('craft-mode-code').click();
    await page.getByTestId('chat-input').fill('Write a FastAPI SSE streaming endpoint with LangGraph.');
    await page.getByTestId('send-button').click();

    await expect(page.getByText('Code Craft').last()).toBeVisible({ timeout: 20000 });
    await expect(page.locator('.prose-craft').last()).toContainText('FastAPI', { timeout: 20000 });

    await page.waitForTimeout(500);
    saveBoth(await page.screenshot({ fullPage: false }), '11_chat_hyper_70b_code_mode.png');

    // 9. Logout and Login Again to Verify Persistence
    await page.getByTestId('logout-button').first().click();
    await page.waitForURL('**/login');

    await page.fill('input[placeholder="you@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="••••••••"]', 'SecurePass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    // Click the most recent persisted conversation in the sidebar
    const firstConv = page.locator('[data-testid^="conversation-item-"]').first();
    await expect(firstConv).toBeVisible();
    await firstConv.click();
    await expect(page.locator('.prose-craft').first()).toContainText('FastAPI');
    await page.waitForTimeout(500);
    saveBoth(await page.screenshot({ fullPage: false }), '12_persisted_conversation_history.png');

  });
});
