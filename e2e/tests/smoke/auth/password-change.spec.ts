/**
 * Password change (while logged in) smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P2, P5, P7
 * @priority P1
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { SecurityPage } from '../../../pages/user/settings.page';
import { LoginPage } from '../../../pages/auth/login.page';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';

test.describe('Password Change', () => {
  test('change password while logged in', async ({ page, apiClient, dbClient }) => {
    // Create a fresh user for this test (we'll modify their password)
    const email = generateEmail('pwd-change');
    const username = usernameFromEmail(email);
    const oldPassword = 'OldPass123!';
    const newPassword = 'NewPass789!';

    const getCode = (e: string) => dbClient.getVerificationCode(e);
    await apiClient.registerAndVerify(email, oldPassword, getCode, username);

    // Login through the browser UI (sets HttpOnly cookie + in-memory token)
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(email, oldPassword);
    await expect(page).toHaveURL(/\/home/);

    // Navigate to security page and wait for it to fully load
    const securityPage = new SecurityPage(page);
    await securityPage.goto();
    await expect(securityPage.heading).toBeVisible({ timeout: 10000 });

    // Change password and wait for success confirmation
    await securityPage.changePassword(oldPassword, newPassword);
    await expect(page.getByText(/password changed successfully/i)).toBeVisible({ timeout: 10000 });

    // Clear cookies to force logout, then login with new password
    await page.context().clearCookies();
    await page.goto('/login');
    const loginPage2 = new LoginPage(page);
    await loginPage2.login(email, newPassword);
    await expect(page).toHaveURL(/\/home/);
  });
});
