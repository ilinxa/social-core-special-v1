/**
 * @layer L1
 * @system cms
 * @parameters P1, P2, P3, P4
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformCmsSitesPage } from '../../../pages/platform/platform-cms.page';
import { CmsSiteDetailPage } from '../../../pages/cms/site-detail.page';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { createCmsSiteViaApi } from '../../../helpers/cms.helper';
import { TEST_USERS } from '../../../lib/constants';

test.describe('CMS Site Management (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('platform admin sees site list page', async ({ platformAdminPage }) => {
    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await sitesPage.goto();
    await expect(sitesPage.heading).toBeVisible();
  });

  test('platform admin can create a site via dialog', async ({
    platformAdminPage,
  }) => {
    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await sitesPage.goto();

    const slug = `e2e-site-${Date.now()}`;
    await sitesPage.createSite({ name: 'Test Site', slug });

    await expect(platformAdminPage.getByText('Test Site')).toBeVisible();
  });

  test('platform admin can view site detail', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Detail Test',
      slug: `e2e-detail-${Date.now()}`,
    });

    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await sitesPage.goto();
    await sitesPage.clickSite('Detail Test');

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await expect(detailPage.siteName).toBeVisible();
    await expect(detailPage.pagesTab).toBeVisible();
    await expect(detailPage.apiKeysTab).toBeVisible();
  });

  test('platform admin can edit a site', async ({ platformAdminPage, apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const slug = `e2e-edit-${Date.now()}`;
    await createCmsSiteViaApi(apiClient, { name: 'Edit Me', slug });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(slug);
    await expect(detailPage.siteName).toBeVisible();
    await detailPage.editButton.click();
    await detailPage.editNameInput.clear();
    await detailPage.editNameInput.fill('Edited Site');
    await detailPage.saveButton.click();

    await expect(platformAdminPage.getByText('Edited Site')).toBeVisible();
  });

  test('platform admin can delete a site', async ({ platformAdminPage, apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const slug = `e2e-del-${Date.now()}`;
    await createCmsSiteViaApi(apiClient, { name: 'Delete Me', slug });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(slug);
    await expect(detailPage.siteName).toBeVisible();
    await detailPage.deleteButton.click();
    await expect(detailPage.deleteConfirmButton).toBeVisible();
    await detailPage.deleteConfirmButton.click();

    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await expect(sitesPage.heading).toBeVisible();
    await expect(platformAdminPage.getByText('Delete Me')).not.toBeVisible();
  });

  test('duplicate slug shows error', async ({ platformAdminPage, apiClient }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const slug = `e2e-dup-${Date.now()}`;
    await createCmsSiteViaApi(apiClient, { name: 'First', slug });

    const sitesPage = new PlatformCmsSitesPage(platformAdminPage);
    await sitesPage.goto();
    await sitesPage.createSite({ name: 'Second', slug });

    // Error should appear
    await expect(
      platformAdminPage.getByText(/already|taken|exists/i).first(),
    ).toBeVisible();
  });
});
