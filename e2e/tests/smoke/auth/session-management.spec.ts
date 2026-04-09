/**
 * Session management smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { SecurityPage } from '../../../pages/user/settings.page';

test.describe('Session Management', () => {
  test('security page renders with session list', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const securityPage = new SecurityPage(page);
    await securityPage.goto();

    await expect(securityPage.heading).toBeVisible();
    await expect(securityPage.sessionsSection).toBeVisible();
  });

  test('change password form is visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const securityPage = new SecurityPage(page);
    await securityPage.goto();

    await expect(securityPage.currentPasswordInput).toBeVisible();
    await expect(securityPage.newPasswordInput).toBeVisible();
    await expect(securityPage.changePasswordButton).toBeVisible();
  });
});
