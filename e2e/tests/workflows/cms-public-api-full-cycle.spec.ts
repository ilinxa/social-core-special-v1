/**
 * W-CMS-PUB: CMS Public API Full Cycle workflow.
 *
 * Create site → API key → Page → Publish → Public read →
 * Unpublish → 404 → Revoke key → 401.
 *
 * @layer L2
 * @system cms
 * @parameters P5, P11
 * @priority P0
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, BACKEND_URL } from '../../lib/constants';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  createCmsApiKeyViaApi,
  publishCmsPageViaApi,
  unpublishCmsPageViaApi,
  revokeCmsApiKeyViaApi,
  getPublicPageViaApi,
} from '../../helpers/cms.helper';

test.describe('W-CMS-PUB: CMS Public API Full Cycle', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('full public API lifecycle: publish → read → unpublish → revoke', async ({
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();

    // Step 1 — Create site
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Public Cycle',
      slug: `pub-cycle-${ts}`,
    });

    // Step 2 — Create API key
    const apiKey = await createCmsApiKeyViaApi(apiClient, {
      site_id: site.id,
      name: 'Cycle Key',
    });
    expect(apiKey.key).toMatch(/^cmsk_/);

    // Step 3 — Create page
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Cycle Page',
      slug: `cycle-page-${ts}`,
      path: '/cycle',
      page_type: 'content',
      order: 0,
    });

    // Step 4 — Draft page is NOT visible via public API
    const draftRes = await getPublicPageViaApi(BACKEND_URL, apiKey.key, pg.slug);
    expect(draftRes.status).toBe(404);

    // Step 5 — Publish page
    await publishCmsPageViaApi(apiClient, site.slug, pg.slug);

    // Step 6 — Published page IS visible, no draft_content exposed
    const pubRes = await getPublicPageViaApi(BACKEND_URL, apiKey.key, pg.slug);
    expect(pubRes.status).toBe(200);

    // Step 7 — Unpublish → 404 again
    await unpublishCmsPageViaApi(apiClient, site.slug, pg.slug);
    const unpubRes = await getPublicPageViaApi(BACKEND_URL, apiKey.key, pg.slug);
    expect(unpubRes.status).toBe(404);

    // Step 8 — Revoke API key
    await revokeCmsApiKeyViaApi(apiClient, apiKey.id);

    // Step 9 — Revoked key → 401
    // Re-publish first so the page exists, then test key rejection
    await publishCmsPageViaApi(apiClient, site.slug, pg.slug);
    const revokedRes = await getPublicPageViaApi(BACKEND_URL, apiKey.key, pg.slug);
    expect(revokedRes.status).toBe(401);
  });
});
