/**
 * Logout smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P2, P5, P14
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BasePage } from '../../../pages/base.page';

test.describe('Logout', () => {
  test('logout clears session and redirects to login', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    await page.goto('/home');
    const basePage = new BasePage(page);
    await basePage.logout();
    await expect(page).toHaveURL(/\/login/);
  });

  test('cannot access protected route after logout', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    await page.goto('/home');
    const basePage = new BasePage(page);
    await basePage.logout();
    await expect(page).toHaveURL(/\/login/);

    // Try to navigate to a protected route
    await page.goto('/profile');
    // Should redirect back to login
    await expect(page).toHaveURL(/\/login/);
  });
});
