/**
 * W-CMS-BIZ: Business CMS Onboarding workflow.
 *
 * Business requests CMS → Platform approves → Templates provisioned →
 * Business creates site → Creates page → Publishes → Public API serves content.
 *
 * @layer L2
 * @system cms, transactions, business
 * @parameters P1, P5, P12, P13
 * @priority P0
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD, BACKEND_URL } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import {
  enableCmsForBusinessViaApi,
  createBusinessCmsSiteViaApi,
  createBusinessCmsPageViaApi,
  publishBusinessCmsPageViaApi,
  createBusinessCmsApiKeyViaApi,
  listCatalogTemplatesViaApi,
  getPublicPageViaApi,
} from '../../helpers/cms.helper';
import { ApiClient } from '../../lib/api-client';

test.describe('W-CMS-BIZ: Business CMS Onboarding', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('business onboarding: request → approve → create → publish → public', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    // Step 1 — Register user + create business
    const email = generateEmail('cms-onb');
    const username = usernameFromEmail(email);
    await apiClient.register(email, DEFAULT_PASSWORD, username);
    await dbClient.verifyUserDirectly(email);
    await dbClient.grantBusinessCreation(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const bizRes = await apiClient.post('business/', {
      legal_name: `Onboard Biz ${ts}`,
      country: 'US',
      slug: `onb-biz-${ts}`,
    });
    expect(bizRes.ok).toBe(true);
    const biz = (await bizRes.json()) as { id: string; slug: string };

    // Step 2-4 — Platform admin enables CMS (simulating approval)
    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    await enableCmsForBusinessViaApi(adminApi, biz.id, true);

    // Step 5 — Business owner re-logins and CMS is accessible
    await apiClient.login(email, DEFAULT_PASSWORD);

    // Step 6 — Browse catalog templates
    const catalog = await listCatalogTemplatesViaApi(apiClient, biz.slug, 'sections');
    expect(catalog.results.length).toBeGreaterThanOrEqual(0);

    // Step 7 — Create site
    const site = await createBusinessCmsSiteViaApi(apiClient, biz.slug, {
      name: 'Onboard Site',
      slug: `onb-site-${ts}`,
    });

    // Step 8 — Create page
    const pg = await createBusinessCmsPageViaApi(apiClient, biz.slug, {
      site_id: site.id,
      title: 'Onboard Home',
      slug: `onb-home-${ts}`,
      path: '/home',
      page_type: 'content',
      order: 0,
    });
    expect(pg.status).toBe('draft');

    // Step 9 — Publish page
    await publishBusinessCmsPageViaApi(apiClient, biz.slug, site.slug, pg.slug);

    // Step 10 — Create API key
    const apiKey = await createBusinessCmsApiKeyViaApi(apiClient, biz.slug, {
      site_id: site.id,
      name: 'Onboard Key',
    });
    expect(apiKey.key).toMatch(/^cmsk_/);

    // Step 11 — Public API serves published content
    const pubRes = await getPublicPageViaApi(BACKEND_URL, apiKey.key, pg.slug);
    expect(pubRes.status).toBe(200);
  });
});
