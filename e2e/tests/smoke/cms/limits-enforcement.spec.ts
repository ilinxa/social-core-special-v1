/**
 * @layer L1
 * @system cms, feature-gates
 * @parameters P7, P14
 * @priority P1
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';
import {
  enableCmsForBusinessViaApi,
  createBusinessCmsSiteViaApi,
  createBusinessCmsPageViaApi,
} from '../../../helpers/cms.helper';
import { ApiClient } from '../../../lib/api-client';

test.describe('CMS Limits Enforcement', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('creating resources within limits succeeds', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    // Setup: create business with CMS
    const email = generateEmail('limits');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await dbClient.grantBusinessCreation(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const bizRes = await apiClient.post('business/', {
      legal_name: `Limits Biz ${ts}`,
      country: 'US',
      slug: `limits-biz-${ts}`,
    });
    const biz = (await bizRes.json()) as { id: string; slug: string };

    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    await enableCmsForBusinessViaApi(adminApi, biz.id, true);

    await apiClient.login(email, DEFAULT_PASSWORD);

    // Create a site — should succeed (default limits are 0 = unlimited)
    const site = await createBusinessCmsSiteViaApi(apiClient, biz.slug, {
      name: 'Limits Test Site',
      slug: `limits-site-${ts}`,
    });
    expect(site.slug).toBeTruthy();

    // Create a page within the site — should succeed
    const page = await createBusinessCmsPageViaApi(apiClient, biz.slug, {
      site_id: site.id,
      title: 'Limits Page',
      slug: `limits-page-${ts}`,
      path: '/limits',
      page_type: 'content',
      order: 0,
    });
    expect(page.slug).toBeTruthy();
  });

  test('multiple sites can be created with unlimited config', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    const email = generateEmail('multi-site');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await dbClient.grantBusinessCreation(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const bizRes = await apiClient.post('business/', {
      legal_name: `Multi Biz ${ts}`,
      country: 'US',
      slug: `multi-biz-${ts}`,
    });
    const biz = (await bizRes.json()) as { id: string; slug: string };

    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    await enableCmsForBusinessViaApi(adminApi, biz.id, true);

    await apiClient.login(email, DEFAULT_PASSWORD);

    // Create 3 sites — should all succeed
    for (let i = 0; i < 3; i++) {
      const site = await createBusinessCmsSiteViaApi(apiClient, biz.slug, {
        name: `Site ${i + 1}`,
        slug: `multi-site-${i}-${ts}`,
      });
      expect(site.slug).toBeTruthy();
    }
  });

  test('multiple pages per site with unlimited config', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    const email = generateEmail('multi-page');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await dbClient.grantBusinessCreation(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const bizRes = await apiClient.post('business/', {
      legal_name: `Pages Biz ${ts}`,
      country: 'US',
      slug: `pages-biz-${ts}`,
    });
    const biz = (await bizRes.json()) as { id: string; slug: string };

    const adminApi = new ApiClient();
    await adminApi.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    await enableCmsForBusinessViaApi(adminApi, biz.id, true);

    await apiClient.login(email, DEFAULT_PASSWORD);

    const site = await createBusinessCmsSiteViaApi(apiClient, biz.slug, {
      name: 'Pages Test',
      slug: `pages-site-${ts}`,
    });

    // Create 3 pages — should all succeed
    for (let i = 0; i < 3; i++) {
      const pg = await createBusinessCmsPageViaApi(apiClient, biz.slug, {
        site_id: site.id,
        title: `Page ${i + 1}`,
        slug: `mp-${i}-${ts}`,
        path: `/page-${i}`,
        page_type: 'content',
        order: i,
      });
      expect(pg.slug).toBeTruthy();
    }
  });

  test('CMS requires cms_enabled flag on business', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    // Create a business WITHOUT CMS enabled
    const email = generateEmail('no-cms');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await dbClient.grantBusinessCreation(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const bizRes = await apiClient.post('business/', {
      legal_name: `No CMS Biz ${ts}`,
      country: 'US',
      slug: `no-cms-${ts}`,
    });
    const biz = (await bizRes.json()) as { id: string; slug: string };

    // Try to create a site without CMS enabled — should fail
    const siteRes = await apiClient.post(`cms/business/${biz.slug}/sites/`, {
      name: 'Should Fail',
      slug: `fail-${ts}`,
    });
    expect(siteRes.ok).toBe(false);
    expect([403, 404]).toContain(siteRes.status);
  });
});
