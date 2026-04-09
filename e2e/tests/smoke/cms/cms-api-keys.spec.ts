/**
 * @layer L1
 * @system cms
 * @parameters P1, P4, P11
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { CmsSiteDetailPage } from '../../../pages/cms/site-detail.page';
import { ApiKeysPanel } from '../../../pages/cms/api-keys.page';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { createCmsSiteViaApi } from '../../../helpers/cms.helper';
import { TEST_USERS } from '../../../lib/constants';

test.describe('CMS API Keys (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('API key list renders in site detail tab', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Key List Site',
      slug: `e2e-keylist-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(platformAdminPage);
    await expect(keysPanel.heading).toBeVisible();
  });

  test('create API key shows one-time reveal with cmsk_ prefix', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Key Reveal Site',
      slug: `e2e-reveal-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(platformAdminPage);
    await keysPanel.createKey('Production Key');

    await expect(keysPanel.revealDialogTitle).toBeVisible();
    await expect(keysPanel.revealedKey).toBeVisible();
    const keyText = await keysPanel.revealedKey.textContent();
    expect(keyText).toMatch(/^cmsk_/);
  });

  test('copy button available in reveal dialog', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Copy Key Site',
      slug: `e2e-copy-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(platformAdminPage);
    await keysPanel.createKey('Copy Key');

    await expect(keysPanel.copyButton).toBeVisible();
  });

  test('key appears in list after dialog close', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'List Check Site',
      slug: `e2e-listcheck-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await expect(detailPage.siteName).toBeVisible();
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(platformAdminPage);
    await expect(keysPanel.heading).toBeVisible();
    await keysPanel.createKey('Listed Key');
    // Wait for reveal dialog then close it
    await expect(keysPanel.revealDialogTitle).toBeVisible();
    await platformAdminPage.keyboard.press('Escape');
    // Wait for reveal dialog to disappear before checking list
    await expect(keysPanel.revealDialogTitle).not.toBeVisible();

    await expect(platformAdminPage.getByText('Listed Key')).toBeVisible();
    await expect(platformAdminPage.getByText(/active/i).first()).toBeVisible();
  });

  test('revoke API key marks it as revoked', async ({
    platformAdminPage,
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.platformAdmin.email, TEST_USERS.platformAdmin.password);
    const site = await createCmsSiteViaApi(apiClient, {
      name: 'Revoke Site',
      slug: `e2e-revoke-${Date.now()}`,
    });

    const detailPage = new CmsSiteDetailPage(platformAdminPage);
    await detailPage.gotoForPlatform(site.slug);
    await expect(detailPage.siteName).toBeVisible();
    await detailPage.apiKeysTab.click();

    const keysPanel = new ApiKeysPanel(platformAdminPage);
    await expect(keysPanel.heading).toBeVisible();
    await keysPanel.createKey('Revocable Key');
    // Wait for reveal dialog then close it
    await expect(keysPanel.revealDialogTitle).toBeVisible();
    await platformAdminPage.keyboard.press('Escape');
    await expect(keysPanel.revealDialogTitle).not.toBeVisible();

    // Wait for key to appear in list before revoking
    await expect(platformAdminPage.getByText('Revocable Key')).toBeVisible();
    await keysPanel.revokeKey('Revocable Key');
    await expect(keysPanel.revokeConfirmButton).toBeVisible();
    await keysPanel.revokeConfirmButton.click();

    await expect(platformAdminPage.getByText(/revoked/i).first()).toBeVisible();
  });
});
