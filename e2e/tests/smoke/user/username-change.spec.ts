/**
 * Username change smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P2, P4, P7
 * @priority P1
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { SettingsPage } from '../../../pages/user/settings.page';
import { LoginPage } from '../../../pages/auth/login.page';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';

test.describe('Username Change', () => {
  test('change username successfully', async ({ page, apiClient, dbClient }) => {
    // Create a fresh user for this test
    const email = generateEmail('uname-change');
    const username = usernameFromEmail(email);
    const password = 'TestPass123!';

    const getCode = (e: string) => dbClient.getVerificationCode(e);
    await apiClient.registerAndVerify(email, password, getCode, username);

    // Login through the browser UI (sets HttpOnly cookie + in-memory token)
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(email, password);
    await expect(page).toHaveURL(/\/home/);

    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();

    const newUsername = `e2e_renamed_${Date.now()}`;
    await settingsPage.changeUsername(newUsername);

    // Wait for mutation to complete (success toast)
    await expect(page.getByText(/username updated/i)).toBeVisible();

    // Verify the change persisted (reload settings)
    await page.reload();
    await expect(settingsPage.usernameInput).toHaveValue(newUsername);
  });
});
