/**
 * Email verification smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P2, P4, P5, P7
 * @priority P0
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { VerifyEmailPage } from '../../../pages/auth/verify-email.page';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';

test.describe('Email Verification', () => {
  test('verify email with correct code redirects to login', async ({ page, apiClient, dbClient }) => {
    const email = generateEmail('verify-ok');
    const username = usernameFromEmail(email);
    await apiClient.register(email, 'TestPass123!', username);

    // Get verification code from DB
    const code = await dbClient.getVerificationCode(email);
    expect(code).not.toBeNull();

    const verifyPage = new VerifyEmailPage(page);
    await verifyPage.goto(email);

    // Email should be pre-filled
    await expect(verifyPage.emailInput).toHaveValue(email);

    await verifyPage.verify(code!);

    // Should redirect to login with verified flag
    await expect(page).toHaveURL(/\/login\?verified=true/);
  });

  test('invalid code shows error', async ({ page, apiClient, dbClient }) => {
    const email = generateEmail('verify-bad');
    const username = usernameFromEmail(email);
    await apiClient.register(email, 'TestPass123!', username);

    // Wait for code to exist
    const code = await dbClient.getVerificationCode(email);
    expect(code).not.toBeNull();

    const verifyPage = new VerifyEmailPage(page);
    await verifyPage.goto(email);
    await verifyPage.verify('000000'); // Wrong code

    await expect(verifyPage.formError).toBeVisible();
    await expect(verifyPage.formError).toContainText(/invalid/i);
  });

  test('resend code button works with cooldown', async ({ page, apiClient }) => {
    const email = generateEmail('verify-resend');
    const username = usernameFromEmail(email);
    await apiClient.register(email, 'TestPass123!', username);

    const verifyPage = new VerifyEmailPage(page);
    await verifyPage.goto(email);

    await verifyPage.resendCode();

    // Button should enter cooldown state
    const isOnCooldown = await verifyPage.isResendOnCooldown();
    expect(isOnCooldown).toBe(true);
  });

  test('verify page renders with email from query param', async ({ page }) => {
    const verifyPage = new VerifyEmailPage(page);
    await verifyPage.goto('test@example.com');

    await expect(verifyPage.cardTitle).toBeVisible();
    await expect(verifyPage.emailInput).toHaveValue('test@example.com');
    await expect(verifyPage.codeInput).toBeVisible();
    await expect(verifyPage.submitButton).toBeVisible();
  });
});
