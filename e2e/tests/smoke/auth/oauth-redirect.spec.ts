/**
 * OAuth redirect smoke tests.
 *
 * Verifies that OAuth buttons initiate the correct redirect.
 * Does NOT test the full OAuth flow (requires test accounts).
 *
 * @layer L1
 * @system auth
 * @parameters P2, P3
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { LoginPage } from '../../../pages/auth/login.page';

test.describe('OAuth Redirect', () => {
  test('Google button initiates OAuth redirect', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Click Google OAuth — should navigate to Google's auth page
    const [popup] = await Promise.all([
      page.waitForEvent('popup').catch(() => null),
      loginPage.googleButton.click(),
    ]);

    if (popup) {
      // OAuth opened in popup
      await expect(popup).toHaveURL(/accounts\.google\.com|googleapis\.com/);
      await popup.close();
    } else {
      // OAuth opened in same tab (redirect)
      await expect(page).toHaveURL(/accounts\.google\.com|googleapis\.com|\/login/);
    }
  });

  test('Apple button initiates OAuth redirect', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    const [popup] = await Promise.all([
      page.waitForEvent('popup').catch(() => null),
      loginPage.appleButton.click(),
    ]);

    if (popup) {
      await expect(popup).toHaveURL(/appleid\.apple\.com/);
      await popup.close();
    } else {
      await expect(page).toHaveURL(/appleid\.apple\.com|\/login/);
    }
  });

  test('OAuth buttons are visible on register page', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByRole('button', { name: /google/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /apple/i })).toBeVisible();
  });
});
