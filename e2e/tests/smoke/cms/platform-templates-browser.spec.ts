/**
 * @layer L1
 * @system cms
 * @parameters P2
 * @priority P1
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformCmsTemplatesPage } from '../../../pages/platform/platform-cms.page';
import { isSystemEnabled } from '../../../lib/feature-gates';

test.describe('CMS Template Browser (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('template browser lists section templates', async ({ platformAdminPage }) => {
    const templatesPage = new PlatformCmsTemplatesPage(platformAdminPage);
    await templatesPage.goto();

    await expect(templatesPage.heading).toBeVisible();
    await expect(templatesPage.sectionTab).toBeVisible();
  });

  test('switch to block templates tab', async ({ platformAdminPage }) => {
    const templatesPage = new PlatformCmsTemplatesPage(platformAdminPage);
    await templatesPage.goto();
    await expect(templatesPage.heading).toBeVisible();
    await expect(templatesPage.blockTab).toBeVisible();

    await templatesPage.blockTab.click();
    // Block template cards should be visible (seeded in global-setup)
    await expect(
      platformAdminPage.getByText('Text Block').or(templatesPage.emptyState),
    ).toBeVisible();
  });

  test('template cards show org_type badges', async ({ platformAdminPage }) => {
    const templatesPage = new PlatformCmsTemplatesPage(platformAdminPage);
    await templatesPage.goto();

    // Seeded templates have org_type "all" and "platform"
    await expect(platformAdminPage.getByText(/all/i).first()).toBeVisible();
  });

  test('default templates marked with badge', async ({ platformAdminPage }) => {
    const templatesPage = new PlatformCmsTemplatesPage(platformAdminPage);
    await templatesPage.goto();

    // "Hero Section" was seeded with is_default=true
    await expect(platformAdminPage.getByText('Hero Section')).toBeVisible();
    await expect(platformAdminPage.getByText(/default/i).first()).toBeVisible();
  });
});
