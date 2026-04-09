/**
 * Auth helper — common authentication operations for test setup.
 *
 * Provides API-direct and UI-based authentication workflows.
 */

import type { Page, Browser } from '@playwright/test';
import { ApiClient } from '../lib/api-client';
import { DbClient } from '../lib/db-client';
import { LoginPage } from '../pages/auth/login.page';
import { RegisterPage } from '../pages/auth/register.page';
import { VerifyEmailPage } from '../pages/auth/verify-email.page';
import { generateEmail, usernameFromEmail } from '../lib/utils';

/**
 * Register a user via API and verify their email directly in the DB.
 *
 * Uses `db.verifyUserDirectly()` (UPDATE is_verified=TRUE) instead of
 * polling for verification codes — much faster and avoids timing issues.
 * The verification code flow is tested explicitly in W17.
 */
export async function registerAndVerifyViaApi(
  api: ApiClient,
  db: DbClient,
  options?: { email?: string; password?: string },
): Promise<{ id: string; email: string; username: string; tokens: { access_token: string; refresh_token: string } }> {
  const email = options?.email ?? generateEmail('auth-helper');
  const password = options?.password ?? 'TestPass123!';
  const username = usernameFromEmail(email);

  // Register via API
  const registerData = await api.register(email, password, username);

  // Verify directly via DB (skip verification code flow — tested in W17)
  await db.verifyUserDirectly(email);

  // Re-login to get tokens with is_verified=true
  const loginData = await api.login(email, password);

  return {
    id: registerData.user.id,
    email,
    username,
    tokens: loginData.tokens,
  };
}

/**
 * Login via API and set the token on the ApiClient.
 * Returns tokens.
 */
export async function loginViaApi(
  api: ApiClient,
  email: string,
  password: string,
): Promise<{ access_token: string; refresh_token: string }> {
  const data = await api.login(email, password);
  return data.tokens;
}

/**
 * Register a fresh user through the browser UI.
 * Does NOT verify email — use verifyViaUi() or verifyViaDb() after.
 */
export async function registerViaUi(
  page: Page,
  options?: { email?: string; username?: string; password?: string },
): Promise<{ email: string; username: string; password: string }> {
  const email = options?.email ?? generateEmail('ui-reg');
  const username = options?.username ?? usernameFromEmail(email);
  const password = options?.password ?? 'TestPass123!';

  const registerPage = new RegisterPage(page);
  await registerPage.goto();
  await registerPage.register(email, username, password);

  return { email, username, password };
}

/**
 * Login through the browser UI.
 */
export async function loginViaUi(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(email, password);
}

/**
 * Verify email through the browser UI using a code from the DB.
 */
export async function verifyEmailViaUi(
  page: Page,
  db: DbClient,
  email: string,
): Promise<void> {
  const code = await db.getVerificationCode(email);
  if (!code) {
    throw new Error(`No verification code found for ${email}`);
  }
  const verifyPage = new VerifyEmailPage(page);
  await verifyPage.goto(email);
  await verifyPage.verify(code);
}

/**
 * Full registration + verification flow via UI.
 */
export async function registerAndVerifyViaUi(
  page: Page,
  db: DbClient,
  options?: { email?: string; password?: string },
): Promise<{ email: string; username: string; password: string }> {
  const result = await registerViaUi(page, options);

  // Verify directly via DB for speed (avoids waiting for email)
  await db.verifyUserDirectly(result.email);

  return result;
}

/**
 * Login a fresh user in a new browser context.
 * Creates a separate context + page, logs in via UI, and returns the page.
 * Caller is responsible for closing the context when done.
 */
export async function loginInNewContext(
  browser: Browser,
  email: string,
  password: string,
): Promise<{ page: Page; context: import('@playwright/test').BrowserContext }> {
  const context = await browser.newContext();
  const page = await context.newPage();
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(email, password);
  await page.waitForURL(/\/(home|dashboard|activity)/);
  return { page, context };
}
