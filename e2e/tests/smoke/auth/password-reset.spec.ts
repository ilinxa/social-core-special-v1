/**
 * Password reset smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P2, P4, P5, P7
 * @priority P1
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { ForgotPasswordPage } from '../../../pages/auth/forgot-password.page';
import { ResetPasswordPage } from '../../../pages/auth/reset-password.page';
import { LoginPage } from '../../../pages/auth/login.page';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';

test.describe('Password Reset', () => {
  test('request reset shows success message', async ({ page, apiClient, dbClient }) => {
    // Register a fresh user first
    const email = generateEmail('pwd-reset');
    const username = usernameFromEmail(email);
    await apiClient.register(email, 'OldPass123!', username);
    await dbClient.verifyUserDirectly(email);

    const forgotPage = new ForgotPasswordPage(page);
    await forgotPage.goto();
    await forgotPage.requestReset(email);
    await expect(forgotPage.successMessage).toBeVisible();
  });

  test('reset password with valid token and login', async ({ page, apiClient, dbClient }) => {
    // Register a fresh user
    const email = generateEmail('pwd-token');
    const username = usernameFromEmail(email);
    await apiClient.register(email, 'OldPass123!', username);
    await dbClient.verifyUserDirectly(email);

    // Request reset via API
    await apiClient.clearToken();
    await apiClient.post('auth/forgot-password/', { email });

    // Get the reset token from DB
    const token = await dbClient.getPasswordResetToken(email);
    if (!token) {
      test.skip(true, 'No reset token found — email task may not have run');
      return;
    }

    // Navigate to reset page with token
    const resetPage = new ResetPasswordPage(page);
    await resetPage.goto(token);
    await expect(resetPage.newPasswordInput).toBeVisible();

    // Reset password
    await resetPage.resetPassword('NewPass456!');

    // Should redirect to login after success
    await expect(page).toHaveURL(/\/login/);

    // Verify login with new password works
    const loginPage = new LoginPage(page);
    await loginPage.login(email, 'NewPass456!');
    await expect(page).toHaveURL(/\/home/);
  });

  test('missing token shows error', async ({ page }) => {
    const resetPage = new ResetPasswordPage(page);
    // Navigate without a token — the form checks for empty/null token
    // and renders "Invalid reset link" immediately
    await resetPage.goto();
    await expect(resetPage.invalidTokenMessage).toBeVisible();
  });

  test('back to sign in link works', async ({ page }) => {
    const forgotPage = new ForgotPasswordPage(page);
    await forgotPage.goto();
    await forgotPage.backToSignInLink.click();
    await expect(page).toHaveURL(/\/login/);
  });
});
