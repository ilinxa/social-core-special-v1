/**
 * CMS fixtures — pre-configured business with CMS enabled.
 *
 * Provides a `businessWithCms` fixture that creates a unique user, business,
 * and enables CMS via the platform admin API. Default templates are auto-provisioned.
 *
 * The businessCmsPage fixture is an authenticated browser page with HttpOnly
 * cookies set — matching the pattern from auth.fixture.ts.
 *
 * Usage:
 * ```typescript
 * import { test, expect } from '../../fixtures/cms.fixture';
 *
 * test('business CMS site CRUD', async ({ businessCmsPage, businessCmsApi, businessSlug }) => {
 *   await businessCmsPage.goto(`/cconsole/${businessSlug}/sites`);
 *   // CMS is already enabled with default templates
 * });
 * ```
 */

import { test as base, type Page, type BrowserContext } from '@playwright/test';
import { ApiClient } from '../lib/api-client';
import { DbClient } from '../lib/db-client';
import { TEST_USERS, DEFAULT_PASSWORD } from '../lib/constants';
import { generateEmail, usernameFromEmail } from '../lib/utils';
import { enableCmsForBusinessViaApi } from '../helpers/cms.helper';

/**
 * Internal state shared between fixtures within a single test.
 * This avoids re-registering the user in each fixture.
 */
type CmsUserState = {
  email: string;
  password: string;
  businessId: string;
  businessSlug: string;
  api: ApiClient;
};

type CmsFixtures = {
  /** HTTP API client for test data setup */
  apiClient: ApiClient;
  /** Direct PostgreSQL client */
  dbClient: DbClient;
  /** Authenticated page for the business owner with CMS enabled */
  businessCmsPage: Page;
  /** API client authenticated as the business owner */
  businessCmsApi: ApiClient;
  /** The business slug for URL construction */
  businessSlug: string;
  /** The business UUID */
  businessId: string;
  /** Internal: shared user state (not for direct test use) */
  _cmsUserState: CmsUserState;
};

export const test = base.extend<CmsFixtures>({
  apiClient: async ({}, use) => {
    await use(new ApiClient());
  },

  dbClient: async ({}, use) => {
    const client = new DbClient();
    await use(client);
    await client.close();
  },

  // Internal fixture: sets up user + business + CMS, shared by other fixtures
  _cmsUserState: async ({ dbClient }, use) => {
    const email = generateEmail('cms-biz');
    const username = usernameFromEmail(email);
    const api = new ApiClient();

    // 1. Register + verify
    await api.register(email, DEFAULT_PASSWORD, username);
    await dbClient.verifyUserDirectly(email);

    // 2. Grant business creation
    await dbClient.grantBusinessCreation(email);

    // 3. Login + create business
    const loginData = await api.login(email, DEFAULT_PASSWORD);

    const bizRes = await api.post('business/', {
      legal_name: `CMS Test Biz ${Date.now()}`,
      country: 'US',
      slug: `cms-biz-${Date.now()}`,
    });
    if (!bizRes.ok) {
      const body = await bizRes.text();
      throw new Error(`Business creation failed: ${bizRes.status} — ${body}`);
    }
    const biz = (await bizRes.json()) as { id: string; slug: string };

    // 4. Enable CMS via platform admin
    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    await enableCmsForBusinessViaApi(adminApi, biz.id, true);

    // 5. Re-login to get fresh token
    await api.login(email, DEFAULT_PASSWORD);

    await use({
      email,
      password: DEFAULT_PASSWORD,
      businessId: biz.id,
      businessSlug: biz.slug,
      api,
    });
  },

  businessCmsApi: async ({ _cmsUserState }, use) => {
    await use(_cmsUserState.api);
  },

  businessSlug: async ({ _cmsUserState }, use) => {
    await use(_cmsUserState.businessSlug);
  },

  businessId: async ({ _cmsUserState }, use) => {
    await use(_cmsUserState.businessId);
  },

  businessCmsPage: async ({ browser, _cmsUserState }, use) => {
    // Login via API to get refresh token for cookie-based auth
    const api = new ApiClient();
    const loginData = await api.login(_cmsUserState.email, _cmsUserState.password);
    const refreshToken = loginData.tokens.refresh_token;

    // Create browser context with auth cookies (same pattern as auth.fixture.ts)
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
        expires: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60,
      },
      {
        name: 'has_session',
        value: '1',
        domain: 'localhost',
        path: '/',
        httpOnly: false,
        secure: false,
        sameSite: 'Lax',
        expires: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60,
      },
    ]);

    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
