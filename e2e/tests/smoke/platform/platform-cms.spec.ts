/**
 * Platform CMS smoke tests.
 *
 * @layer L1
 * @system cms
 * @parameters P1, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import {
  PlatformCmsSitesPage,
  PlatformCmsTemplatesPage,
  PlatformCmsApiKeysPage,
  PlatformMediaPage,
} from '../../../pages/platform/platform-cms.page';

test.describe('Platform CMS', () => {
  test('CMS sites page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const sitesPage = new PlatformCmsSitesPage(page);
    await sitesPage.goto();

    await expect(sitesPage.heading).toBeVisible();
  });

  test('CMS templates page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const templatesPage = new PlatformCmsTemplatesPage(page);
    await templatesPage.goto();

    await expect(templatesPage.heading).toBeVisible();
  });

  test('API keys page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const keysPage = new PlatformCmsApiKeysPage(page);
    await keysPage.goto();

    await expect(keysPage.heading).toBeVisible();
  });

  test('media library page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const mediaPage = new PlatformMediaPage(page);
    await mediaPage.goto();

    await expect(mediaPage.heading).toBeVisible();
  });
});
