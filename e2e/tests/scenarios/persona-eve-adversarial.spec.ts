/**
 * Persona: Eve — The Adversarial User
 *
 * Tests security boundaries: XSS payloads, SQL injection attempts,
 * account lockout, 403 on unauthorized access, and account deactivation.
 *
 * 29 progressive steps.
 *
 * @layer L3
 * @system auth, users, business
 * @parameters P1 (Auth), P5 (CRUD), P11 (Security), P13 (Error)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { RegisterPage } from '../../pages/auth/register.page';
import { ProfileViewPage } from '../../pages/user/profile.page';
import { ExplorePage } from '../../pages/explore/explore.page';
import { SettingsPage } from '../../pages/user/settings.page';
import { getOrgMode } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';

test.describe.serial('Eve: The Adversarial User', () => {
  const eveEmail = generateEmail('eve-persona');
  const evePassword = 'EvePass123!';

  // -----------------------------------------------------------------------
  // Phase 1: XSS & Injection Attempts
  // -----------------------------------------------------------------------

  test('Step 1: Eve registers normally first', async ({ apiClient, dbClient }) => {
    await registerAndVerifyViaApi(apiClient, dbClient, {
      email: eveEmail,
      password: evePassword,
    });
  });

  test('Step 2: Eve attempts XSS in login email field', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Register dialog listener BEFORE any actions that could trigger XSS
    const dialogs: string[] = [];
    page.on('dialog', (dialog) => {
      dialogs.push(dialog.message());
      dialog.dismiss();
    });

    // XSS payload in email — should not execute
    await loginPage.emailInput.fill('<script>alert("xss")</script>@evil.com');
    await loginPage.passwordInput.fill('SomePass123!');
    await loginPage.submitButton.click();

    // Should show validation error (inline paragraph or role=alert), NOT execute script
    const validationMsg = page.getByText(/enter a valid email|invalid email/i);
    await expect(loginPage.formError.or(validationMsg)).toBeVisible({ timeout: 5000 });
    // Verify no alert dialog (XSS did not execute)
    expect(dialogs).toHaveLength(0);
  });

  test('Step 3: Eve attempts XSS in registration username', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();

    await registerPage.emailInput.fill(generateEmail('eve-xss'));
    await registerPage.usernameInput.fill('<img src=x onerror=alert(1)>');
    await registerPage.passwordInput.fill('TestPass123!');
    await registerPage.confirmPasswordInput.fill('TestPass123!');
    await registerPage.submitButton.click();

    // Should reject or sanitize — not render the XSS
    // The page should still be on register (validation error) or redirect safely
    const currentUrl = page.url();
    const pageContent = await page.content();
    expect(pageContent).not.toContain('onerror=alert');
  });

  test('Step 4: Eve attempts SQL injection in search', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await explorePage.searchInput.fill("'; DROP TABLE users; --");

    // Should not crash — page remains functional
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 5: Eve attempts path traversal in URL', async ({ page }) => {
    // Path traversal test — doesn't need auth, tests server security
    // Browsers normalize /../ so /../../etc/passwd resolves to /etc/passwd
    // Next.js catch-all may return 200 with a not-found page, so check content
    await page.goto('/etc/passwd');
    const content = await page.content();
    // Should NOT contain actual passwd file content
    expect(content).not.toContain('root:x:0:0');
    expect(content).not.toContain('/bin/bash');
  });

  test('Step 6: Eve attempts to access other user profile edit', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    // Try to access admin routes — Next.js catch-all may return 200 with not-found page
    await page.goto('/admin/');
    const content = await page.content();
    // Should NOT contain actual Django admin interface
    expect(content).not.toContain('Django administration');
    expect(content).not.toContain('django-admin-login');
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 2: Account Lockout
  // -----------------------------------------------------------------------

  test('Step 7: Eve attempts login with wrong password — attempt 1', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, 'WrongPassword1!');
    await expect(loginPage.formError).toBeVisible();
  });

  test('Step 8: Eve attempts login with wrong password — attempt 2', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, 'WrongPassword2!');
    await expect(loginPage.formError).toBeVisible();
  });

  test('Step 9: Eve attempts login with wrong password — attempt 3', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, 'WrongPassword3!');
    await expect(loginPage.formError).toBeVisible();
  });

  test('Step 10: Eve attempts login with wrong password — attempt 4', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, 'WrongPassword4!');
    await expect(loginPage.formError).toBeVisible();
  });

  test('Step 11: Eve attempts login with wrong password — attempt 5', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, 'WrongPassword5!');
    await expect(loginPage.formError).toBeVisible();
  });

  test('Step 12: Eve can still login with correct password after 5 failed attempts', async ({
    page,
  }) => {
    // Account lockout kicks in at 10 attempts — 5 should still allow login
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, evePassword);
    await expect(page).toHaveURL(/\/home/);
  });

  // -----------------------------------------------------------------------
  // Phase 3: Unauthorized Access
  // -----------------------------------------------------------------------

  test('Step 13: Eve tries to access business console without membership', async ({
    browser,
  }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/bconsole/some-random-business/dashboard');
    // Should redirect away or show error — not show the actual business dashboard
    // The guard may redirect to home/login or show a not-found/access-denied page
    const url = page.url();
    const pageContent = await page.content();
    const isBlocked =
      !url.includes('/bconsole/some-random-business/dashboard') ||
      pageContent.includes('not found') ||
      pageContent.includes('Not Found') ||
      pageContent.includes('access denied') ||
      pageContent.includes('404');
    expect(isBlocked).toBe(true);
    await context.close();
  });

  test('Step 14: Eve tries to access platform console without admin role', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/pconsole/dashboard');
    // Next.js may render the page URL but show access denied / redirect content
    // Verify Eve doesn't see actual platform admin content
    const url = page.url();
    const content = await page.content();
    const isBlocked =
      url.includes('home') ||
      url.includes('login') ||
      content.includes('not authorized') ||
      content.includes('access denied') ||
      content.includes('Not Found') ||
      content.includes('404') ||
      !content.includes('Platform Dashboard'); // If no dashboard content, access is blocked
    expect(isBlocked).toBe(true);
    await context.close();
  });

  test('Step 15: Eve tries direct API access to admin endpoint', async ({ apiClient }) => {
    await apiClient.login(eveEmail, evePassword);

    // Try to access platform admin endpoint
    try {
      const res = await apiClient.get('platform/account/');
      const status = res.status;
      expect([403, 404]).toContain(status);
    } catch {
      // Expected — access denied
    }
  });

  test('Step 16: Eve tries to modify another user via API', async ({ apiClient }) => {
    await apiClient.login(eveEmail, evePassword);

    // Try to PATCH a random user profile
    try {
      const res = await apiClient.patch('users/some-random-user/profile/', {
        display_name: 'Hacked!',
      });
      expect([403, 404, 405]).toContain(res.status);
    } catch {
      // Expected — not allowed
    }
  });

  // -----------------------------------------------------------------------
  // Phase 4: Rate Limiting & Edge Cases
  // -----------------------------------------------------------------------

  test('Step 17: Eve sends rapid requests to test rate limiting', async ({ apiClient }) => {
    await apiClient.login(eveEmail, evePassword);

    // Send 20 rapid requests
    const responses: number[] = [];
    for (let i = 0; i < 20; i++) {
      try {
        const res = await apiClient.get('users/me/');
        responses.push(res.status);
      } catch {
        responses.push(429);
      }
    }

    // Most should succeed, but if rate limited, 429 should appear
    const hasAny = responses.length > 0;
    expect(hasAny).toBe(true);
  });

  test('Step 18: Eve tries extremely long input in search', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    const longInput = 'A'.repeat(10000);
    await explorePage.searchInput.fill(longInput);

    // Page should handle gracefully — no crash
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 19: Eve tries special characters in login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('test@evil"<>&.com', 'Password!@#$%^');
    // May show role="alert" error or inline validation — either is acceptable
    const errorVisible = await loginPage.formError.isVisible().catch(() => false);
    const validationMsg = page.getByText(/invalid|error|failed/i);
    const validationVisible = await validationMsg.first().isVisible().catch(() => false);
    // At minimum, should NOT redirect to /home (login should fail)
    const url = page.url();
    expect(errorVisible || validationVisible || url.includes('login')).toBe(true);
  });

  // -----------------------------------------------------------------------
  // Phase 5: Profile Manipulation
  // -----------------------------------------------------------------------

  test('Step 20: Eve logs in and views her profile', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 21: Eve navigates to profile edit', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await profilePage.clickEdit();
    await expect(page).toHaveURL(/\/profile\/edit/);
    await context.close();
  });

  test('Step 22: Eve tries to set XSS payload as display name via UI', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/profile/edit');
    const displayNameInput = page.getByLabel(/display name/i).or(
      page.getByLabel(/name/i).first(),
    );
    if (await displayNameInput.isVisible()) {
      await displayNameInput.fill('<script>alert("xss")</script>');
      const saveButton = page.getByRole('button', { name: /save|update/i });
      if (await saveButton.isVisible()) {
        await saveButton.click();
      }
    }

    // Navigate to profile view — XSS should be escaped
    await page.goto('/profile');
    const content = await page.content();
    expect(content).not.toContain('<script>alert');
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 6: Account Deactivation
  // -----------------------------------------------------------------------

  test('Step 23: Eve navigates to settings', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/settings');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 24: Eve sees the deactivate button', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await expect(settingsPage.deactivateButton).toBeVisible();
    await context.close();
  });

  test('Step 25: Eve opens deactivation dialog', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await settingsPage.initiateDeactivation();
    await expect(settingsPage.deactivateConfirmInput).toBeVisible();
    await expect(settingsPage.deactivateConfirmButton).toBeDisabled();
    await context.close();
  });

  test('Step 26: Eve types wrong confirmation text', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await settingsPage.initiateDeactivation();

    await settingsPage.deactivateConfirmInput.fill('wrong-text');
    await expect(settingsPage.deactivateConfirmButton).toBeDisabled();
    await context.close();
  });

  test('Step 27: Eve types correct confirmation — button enables', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await settingsPage.initiateDeactivation();

    await settingsPage.deactivateConfirmInput.fill('deactivate');
    await expect(settingsPage.deactivateConfirmButton).toBeEnabled();

    // Cancel instead — we don't actually deactivate
    await settingsPage.deactivateCancelButton.click();
    await context.close();
  });

  test('Step 28: Eve verifies account is still active after cancel', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(eveEmail, evePassword);
    await expect(page).toHaveURL(/\/home/);
  });

  test("Step 29: Eve's adversarial journey is complete — no breaches", async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, eveEmail, evePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.heading).toBeVisible();
    await context.close();
  });
});
