/**
 * W-CMS-ISO: CMS Cross-Context Isolation workflow.
 *
 * Two businesses with CMS → Each creates sites → Complete isolation verified.
 *
 * @layer L2
 * @system cms, business
 * @parameters P6
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import {
  enableCmsForBusinessViaApi,
  createBusinessCmsSiteViaApi,
  listBusinessCmsSitesViaApi,
} from '../../helpers/cms.helper';
import { ApiClient } from '../../lib/api-client';

test.describe('W-CMS-ISO: CMS Cross-Context Isolation', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('two businesses cannot see each other CMS sites', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();
    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);

    // Step 1 — Create Business A + enable CMS
    const emailA = generateEmail('iso-a');
    const apiA = new ApiClient();
    await apiA.register(emailA, DEFAULT_PASSWORD, usernameFromEmail(emailA));
    await dbClient.verifyUserDirectly(emailA);
    await dbClient.grantBusinessCreation(emailA);
    await apiA.login(emailA, DEFAULT_PASSWORD);

    const bizARes = await apiA.post('business/', {
      legal_name: `Iso Biz A ${ts}`,
      country: 'US',
      slug: `iso-a-${ts}`,
    });
    const bizA = (await bizARes.json()) as { id: string; slug: string };
    await enableCmsForBusinessViaApi(adminApi, bizA.id, true);
    await apiA.login(emailA, DEFAULT_PASSWORD);

    // Step 2 — Create Business B + enable CMS
    const emailB = generateEmail('iso-b');
    const apiB = new ApiClient();
    await apiB.register(emailB, DEFAULT_PASSWORD, usernameFromEmail(emailB));
    await dbClient.verifyUserDirectly(emailB);
    await dbClient.grantBusinessCreation(emailB);
    await apiB.login(emailB, DEFAULT_PASSWORD);

    const bizBRes = await apiB.post('business/', {
      legal_name: `Iso Biz B ${ts}`,
      country: 'US',
      slug: `iso-b-${ts}`,
    });
    const bizB = (await bizBRes.json()) as { id: string; slug: string };
    await enableCmsForBusinessViaApi(adminApi, bizB.id, true);
    await apiB.login(emailB, DEFAULT_PASSWORD);

    // Step 3 — A creates site "alpha"
    const siteA = await createBusinessCmsSiteViaApi(apiA, bizA.slug, {
      name: 'Alpha Site',
      slug: `alpha-${ts}`,
    });

    // Step 4 — B creates site "beta"
    const siteB = await createBusinessCmsSiteViaApi(apiB, bizB.slug, {
      name: 'Beta Site',
      slug: `beta-${ts}`,
    });

    // Step 5 — A lists sites → only sees "alpha"
    const sitesA = await listBusinessCmsSitesViaApi(apiA, bizA.slug);
    const slugsA = sitesA.results.map((s: Record<string, unknown>) => s.slug);
    expect(slugsA).toContain(`alpha-${ts}`);
    expect(slugsA).not.toContain(`beta-${ts}`);

    // Step 6 — B lists sites → only sees "beta"
    const sitesB = await listBusinessCmsSitesViaApi(apiB, bizB.slug);
    const slugsB = sitesB.results.map((s: Record<string, unknown>) => s.slug);
    expect(slugsB).toContain(`beta-${ts}`);
    expect(slugsB).not.toContain(`alpha-${ts}`);

    // Step 7 — A cannot access B's site (404 or 403)
    const crossRes = await apiA.get(`cms/business/${bizB.slug}/sites/${siteB.slug}/`);
    expect([403, 404]).toContain(crossRes.status);
  });
});
