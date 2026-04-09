/**
 * W18: CMS Content Lifecycle workflow.
 *
 * Full lifecycle: create site → create page → navigate to editor → publish →
 * verify published → unpublish → verify draft → navigate back.
 *
 * @layer L2
 * @system cms, platform
 * @parameters P1, P3, P5
 * @priority P0
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS } from '../../lib/constants';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  publishCmsPageViaApi,
  unpublishCmsPageViaApi,
  getCmsPageViaApi,
} from '../../helpers/cms.helper';
import { PageEditorPage } from '../../pages/cms/page-editor.page';
import { PlatformCmsSitesPage } from '../../pages/platform/platform-cms.page';

test.describe('W18: CMS Content Lifecycle', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('platform admin creates site, publishes page, then unpublishes', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();

    // Step 1 — Create site via API
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'W18 Lifecycle',
      slug: `w18-lc-${ts}`,
    });

    // Step 2 — Create page via API
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Lifecycle Page',
      slug: `lc-page-${ts}`,
      path: '/lifecycle',
      page_type: 'content',
      order: 0,
    });

    // Step 3 — Navigate to page editor UI
    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, pg.slug);
    await expect(editor.pageTitle).toBeVisible();

    // Step 4 — Publish via API
    await publishCmsPageViaApi(apiClient, site.slug, pg.slug);

    // Step 5 — Verify published status via API
    const pubData = await getCmsPageViaApi(apiClient, site.slug, pg.slug);
    expect(pubData.status).toBe('published');

    // Step 6 — Unpublish via API
    await unpublishCmsPageViaApi(apiClient, site.slug, pg.slug);

    // Step 7 — Verify draft status via API
    const draftData = await getCmsPageViaApi(apiClient, site.slug, pg.slug);
    expect(draftData.status).toBe('draft');

    // Step 8 — Navigate to site list, verify site visible
    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await sitesPage.goto();
    await expect(platformAdminPage.getByText('W18 Lifecycle')).toBeVisible();
  });
});
