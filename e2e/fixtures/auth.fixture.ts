/**
 * Auth fixtures — pre-authenticated pages for different roles.
 *
 * Each fixture creates its own independent login session via API, avoiding
 * the token rotation / replay detection issue that occurs when parallel workers
 * share the same refresh token from a storage state file.
 *
 * Usage:
 * ```typescript
 * import { test, expect } from '../../fixtures/auth.fixture';
 *
 * test('business console renders', async ({ businessOwnerPage }) => {
 *   await businessOwnerPage.goto('/bconsole/my-biz');
 *   // Already authenticated as business owner
 * });
 * ```
 */

import { test as base, type Page, type BrowserContext } from '@playwright/test';
import { TEST_USERS, API_URL, BASE_URL } from '../lib/constants';
import { ApiClient } from '../lib/api-client';
import { DbClient } from '../lib/db-client';

type AuthFixtures = {
  /** HTTP API client for test data setup */
  apiClient: ApiClient;
  /** Direct PostgreSQL client */
  dbClient: DbClient;
  /** Page authenticated as a regular user */
  authenticatedPage: Page;
  /** Page authenticated as a business owner */
  businessOwnerPage: Page;
  /** Page authenticated as a business member (not owner) */
  businessMemberPage: Page;
  /** Page authenticated as a platform admin */
  platformAdminPage: Page;
};

/**
 * Create an authenticated browser page by logging in via the backend API.
 *
 * Each call creates a fresh, independent session (unique refresh token) so
 * parallel workers never share tokens — avoiding replay-detection logout.
 *
 * Cookies are set with sameSite:Lax (relaxed from Strict) because Playwright's
 * first navigation from about:blank is treated as cross-site, and Strict
 * cookies are not sent. Lax matches real-user navigation behavior (bookmarks,
 * address bar, link clicks all send Lax cookies).
 */
async function createAuthPage(
  browser: import('@playwright/test').Browser,
  email: string,
  password: string,
): Promise<{ page: Page; context: BrowserContext }> {
  // Random initial delay to stagger concurrent workers (prevents thundering herd)
  await new Promise((r) => setTimeout(r, Math.random() * 500));

  // Login via backend API with retry (concurrent workers can cause transient 500s)
  const api = new ApiClient();
  let loginData;
  for (let attempt = 1; attempt <= 5; attempt++) {
    try {
      loginData = await api.login(email, password);
      break;
    } catch (error) {
      if (attempt === 5) throw error;
      // Exponential backoff + jitter
      await new Promise((r) => setTimeout(r, 1000 * attempt + Math.random() * 1000));
    }
  }
  const refreshToken = loginData!.tokens.refresh_token;

  // Create a fresh browser context and set auth cookies manually
  const context = await browser.newContext();
  await context.addCookies([
    {
      name: 'refresh_token',
      value: refreshToken,
      domain: 'localhost',
      path: '/api/',
      httpOnly: true,
      secure: false,
      sameSite: 'Lax',
      expires: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60, // 7 days
    },
    {
      name: 'has_session',
      value: '1',
      domain: 'localhost',
      path: '/',
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
      expires: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60, // 7 days
    },
  ]);

  const page = await context.newPage();

  return { page, context };
}

export const test = base.extend<AuthFixtures>({
  apiClient: async ({}, use) => {
    await use(new ApiClient());
  },

  dbClient: async ({}, use) => {
    const client = new DbClient();
    await use(client);
    await client.close();
  },

  authenticatedPage: async ({ browser }, use) => {
    const { page, context } = await createAuthPage(
      browser,
      TEST_USERS.regular.email,
      TEST_USERS.regular.password,
    );
    await use(page);
    await context.close();
  },

  businessOwnerPage: async ({ browser }, use) => {
    const { page, context } = await createAuthPage(
      browser,
      TEST_USERS.businessOwner.email,
      TEST_USERS.businessOwner.password,
    );
    await use(page);
    await context.close();
  },

  businessMemberPage: async ({ browser }, use) => {
    const { page, context } = await createAuthPage(
      browser,
      TEST_USERS.businessMember.email,
      TEST_USERS.businessMember.password,
    );
    await use(page);
    await context.close();
  },

  platformAdminPage: async ({ browser }, use) => {
    const { page, context } = await createAuthPage(
      browser,
      TEST_USERS.platformAdmin.email,
      TEST_USERS.platformAdmin.password,
    );
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
