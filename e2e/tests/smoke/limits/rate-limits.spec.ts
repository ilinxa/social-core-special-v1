/**
 * Rate limit / account lockout smoke tests.
 *
 * Verifies that the UI communicates account lockout after repeated
 * failed login attempts. Backend enforces lockout after 10 failed
 * attempts → 15 minute lockout with "Account temporarily locked" message.
 *
 * Note: DRF throttle rates are relaxed in local_docker settings
 * (login: 1000/minute) so we test application-level lockout instead.
 *
 * @layer L1
 * @system auth, limits
 * @parameters P1, P4, P10
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { LoginPage } from '../../../pages/auth/login.page';
import { generateEmail } from '../../../lib/utils';

test.describe('Rate Limits', () => {
  test('account lockout after repeated failed logins shows error', async ({ page, apiClient, dbClient }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Register a real user (lockout only tracks existing users)
    const email = generateEmail();
    await apiClient.registerAndVerify(email, 'TestPass123!', (e) => dbClient.getVerificationCode(e));

    // Attempt 11 wrong-password logins (lockout threshold is 10)
    for (let i = 0; i < 11; i++) {
      await loginPage.login(email, 'WrongPassword!');
      // Wait for the error message to appear before next attempt
      await expect(loginPage.formError).toBeVisible({ timeout: 5000 });
    }

    // After 11 failed attempts, backend returns AccountLocked (401)
    // Message: "Account temporarily locked due to too many failed attempts"
    // LoginForm has no custom handler for account_locked → fallback shows error.message
    await expect(
      loginPage.formError.filter({ hasText: /locked|too many failed attempts/i }),
    ).toBeVisible({ timeout: 10000 });
  });

  test('failed login attempt shows inline error message', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Submit invalid credentials — formError (role="alert") becomes visible
    await loginPage.login('nonexistent@e2e.test', 'WrongPassword!');
    await expect(loginPage.formError).toBeVisible();
    await expect(loginPage.formError).toContainText(/invalid email or password/i);
  });
});
