/**
 * W17: Registration → Email Verification workflow.
 *
 * Verifies the registration flow: fill form, submit, verify email via API
 * (the verify-email page is not yet built in the frontend), then login.
 *
 * @layer L2
 * @system auth
 * @parameters P1 (Auth), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { RegisterPage } from '../../pages/auth/register.page';
import { LoginPage } from '../../pages/auth/login.page';

test.describe('W17: Registration → Email Verification', () => {
  test('user registers via UI, verifies email via API, and can login', async ({
    page,
    apiClient,
    dbClient,
  }) => {
    const email = generateEmail('w17-reg');
    const username = usernameFromEmail(email);
    const password = DEFAULT_PASSWORD;

    // Step 1 — Navigate to /register
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await expect(registerPage.cardTitle).toBeVisible();

    // Step 2 — Fill registration form and submit
    await registerPage.register(email, username, password);

    // Step 3 — Wait for navigation (may go to /verify-email stub or /home)
    await page.waitForURL(/\/(verify-email|home)/, { timeout: 15000 }).catch(() => {
      // May not redirect — continue
    });

    // Step 4 — Get verification code from DB
    const code = await dbClient.getVerificationCode(email);
    expect(code).toBeTruthy();

    // Step 5 — Verify email via API (frontend verify page not yet built)
    const verifyRes = await apiClient.post('auth/verify-email/', {
      email,
      code: code!,
    });
    expect(verifyRes.status).toBeLessThan(300);

    // Step 6 — Clear browser auth state (registration stored tokens)
    await page.context().clearCookies();
    await page.evaluate(() => {
      try { localStorage.clear(); } catch { /* ignore */ }
      try { sessionStorage.clear(); } catch { /* ignore */ }
    });

    // Step 7 — Navigate to /login and login with registered credentials
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await expect(loginPage.emailInput).toBeVisible({ timeout: 10000 });
    await loginPage.login(email, password);

    // Step 8 — Expect redirect to /home (verified user can access app)
    await page.waitForURL(/\/home/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('verification code is generated in DB after registration', async ({
    apiClient,
    dbClient,
  }) => {
    const email = generateEmail('w17-code');
    const username = usernameFromEmail(email);
    const password = DEFAULT_PASSWORD;

    // Register via API
    await apiClient.register(email, password, username);

    // Verify code exists in DB
    const code = await dbClient.getVerificationCode(email);
    expect(code).toBeTruthy();
    expect(code!.length).toBe(6);

    // Verify the code works via API
    const verifyRes = await apiClient.post('auth/verify-email/', {
      email,
      code: code!,
    });
    expect(verifyRes.status).toBeLessThan(300);
  });
});
