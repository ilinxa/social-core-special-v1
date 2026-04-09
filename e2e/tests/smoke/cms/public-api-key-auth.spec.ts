/**
 * @layer L1
 * @system cms
 * @parameters P11
 * @priority P0
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { BACKEND_URL, TEST_USERS } from '../../../lib/constants';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  createCmsApiKeyViaApi,
  publishCmsPageViaApi,
  revokeCmsApiKeyViaApi,
  getPublicSiteViaApi,
  getPublicPageViaApi,
} from '../../../helpers/cms.helper';

test.describe('CMS Public API Key Authentication', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('public site with valid API key returns 200', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Public Site',
      slug: `pub-site-${ts}`,
    });
    const apiKey = await createCmsApiKeyViaApi(apiClient, {
      site_id: site.id,
      name: 'Test Key',
    });

    const res = await getPublicSiteViaApi(BACKEND_URL, apiKey.key, site.slug);
    expect(res.status).toBe(200);
  });

  test('public site without API key returns 401', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'No Key Site',
      slug: `nokey-${Date.now()}`,
    });

    const res = await getPublicSiteViaApi(BACKEND_URL, '', site.slug);
    expect(res.status).toBe(401);
  });

  test('public site with invalid API key returns 401', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Bad Key Site',
      slug: `badkey-${Date.now()}`,
    });

    const res = await getPublicSiteViaApi(
      BACKEND_URL,
      'cmsk_invalid_key_value',
      site.slug,
    );
    expect(res.status).toBe(401);
  });

  test('published page returns content via public API', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Content Site',
      slug: `content-${ts}`,
    });
    const page = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Public Page',
      slug: `pub-page-${ts}`,
      path: '/pub',
      page_type: 'content',
      order: 0,
    });
    await publishCmsPageViaApi(apiClient, site.slug, page.slug);
    const apiKey = await createCmsApiKeyViaApi(apiClient, {
      site_id: site.id,
      name: 'Content Key',
    });

    const res = await getPublicPageViaApi(BACKEND_URL, apiKey.key, page.slug);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).not.toHaveProperty('draft_content');
  });

  test('draft page returns 404 via public API', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Draft Site',
      slug: `draft-${ts}`,
    });
    const page = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Draft Page',
      slug: `draft-page-${ts}`,
      path: '/draft',
      page_type: 'content',
      order: 0,
    });
    const apiKey = await createCmsApiKeyViaApi(apiClient, {
      site_id: site.id,
      name: 'Draft Key',
    });

    const res = await getPublicPageViaApi(BACKEND_URL, apiKey.key, page.slug);
    expect(res.status).toBe(404);
  });

  test('revoked key returns 401', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Revoke Site',
      slug: `revoke-${ts}`,
    });
    const apiKey = await createCmsApiKeyViaApi(apiClient, {
      site_id: site.id,
      name: 'Revoke Key',
    });

    // Revoke the key
    await revokeCmsApiKeyViaApi(apiClient, apiKey.id);

    const res = await getPublicSiteViaApi(BACKEND_URL, apiKey.key, site.slug);
    expect(res.status).toBe(401);
  });
});
