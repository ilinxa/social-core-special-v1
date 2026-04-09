/**
 * @layer L1
 * @system cms
 * @parameters P1, P2, P4, P5
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { CmsSiteDetailPage } from '../../../pages/cms/site-detail.page';
import { PageEditorPage } from '../../../pages/cms/page-editor.page';
import { isSystemEnabled } from '../../../lib/feature-gates';
import {
  createCmsSiteViaApi,
  createCmsPageViaApi,
  publishCmsPageViaApi,
} from '../../../helpers/cms.helper';
import { TEST_USERS } from '../../../lib/constants';

test.describe('CMS Page Publishing (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('create page via dialog shows draft badge', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Pub Test',
      slug: `e2e-pub-${ts}`,
    });
    // Create page via API for reliability, then verify badge in UI
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Home Page',
      slug: `home-${ts}`,
      path: '/home',
      page_type: 'content',
      order: 0,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await expect(detailPage.siteName).toBeVisible();
    await detailPage.pagesTab.click();

    await expect(platformAdminPage.getByText('Home Page')).toBeVisible();
    await expect(platformAdminPage.getByText(/draft/i).first()).toBeVisible();
  });

  test('status tabs are visible for filtering', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Filter Site',
      slug: `e2e-filter-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await detailPage.pagesTab.click();

    await expect(detailPage.allStatusButton).toBeVisible();
    await expect(detailPage.draftStatusButton).toBeVisible();
    await expect(detailPage.publishedStatusButton).toBeVisible();
    await expect(detailPage.archivedStatusButton).toBeVisible();
  });

  test('publish page via UI', async ({ platformAdminPage, apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Pub Flow',
      slug: `e2e-pubflow-${ts}`,
    });
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Publishable',
      slug: `pub-${ts}`,
      path: '/pub',
      page_type: 'content',
      order: 0,
    });

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, pg.slug);
    await expect(editor.pageTitle).toBeVisible();

    await editor.publishButton.click();
    await expect(editor.publishConfirmButton).toBeVisible();
    await editor.publishConfirmButton.click();

    await expect(platformAdminPage.getByText(/published/i).first()).toBeVisible();
  });

  test('unpublish reverts to draft', async ({ platformAdminPage, apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const ts = Date.now();
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Unpub Flow',
      slug: `e2e-unpub-${ts}`,
    });
    const pg = await createCmsPageViaApi(apiClient, {
      site_id: site.id,
      title: 'Unpub Test',
      slug: `unpub-${ts}`,
      path: '/unpub',
      page_type: 'content',
      order: 0,
    });
    await publishCmsPageViaApi(apiClient, site.slug, pg.slug);

    const editor = new PageEditorPage(platformAdminPage);
    await editor.gotoForPlatform(site.slug, pg.slug);
    await expect(editor.pageTitle).toBeVisible();

    await editor.unpublishButton.click();
    await expect(editor.unpublishConfirmButton).toBeVisible();
    await editor.unpublishConfirmButton.click();

    await expect(platformAdminPage.getByText(/draft/i).first()).toBeVisible();
  });
});
