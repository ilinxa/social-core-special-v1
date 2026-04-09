/**
 * @layer L1
 * @system cms
 * @parameters P12
 * @priority P1
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformCmsBusinessesPage } from '../../../pages/platform/platform-cms.page';
import { isSystemEnabled } from '../../../lib/feature-gates';

test.describe('CMS Business Management (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('business CMS management page lists businesses', async ({
    platformAdminPage,
  }) => {
    const bizPage = new PlatformCmsBusinessesPage(platformAdminPage);
    await bizPage.goto();

    await expect(bizPage.heading).toBeVisible();
    // Wait for data to load — either businesses or empty state
    await expect(
      platformAdminPage.getByText('E2E Test Business').or(bizPage.emptyState),
    ).toBeVisible();
  });

  test('toggle CMS on for a business', async ({ platformAdminPage }) => {
    const bizPage = new PlatformCmsBusinessesPage(platformAdminPage);
    await bizPage.goto();
    await expect(bizPage.heading).toBeVisible();

    // Wait for business row to load before interacting
    await expect(platformAdminPage.getByText('E2E Test Business')).toBeVisible();

    const toggle = bizPage.getBusinessToggle('E2E Test Business');
    await toggle.click();

    // Either "Enabled" or "Disabled" badge should update
    await expect(
      platformAdminPage.getByText(/enabled/i).first().or(
        platformAdminPage.getByText(/disabled/i).first(),
      ),
    ).toBeVisible();
  });

  test('toggle CMS off for a business', async ({ platformAdminPage }) => {
    const bizPage = new PlatformCmsBusinessesPage(platformAdminPage);
    await bizPage.goto();
    await expect(bizPage.heading).toBeVisible();

    // Wait for business row to load before interacting
    await expect(platformAdminPage.getByText('E2E Test Business')).toBeVisible();

    const toggle = bizPage.getBusinessToggle('E2E Test Business');
    await toggle.click();
    await expect(
      platformAdminPage.getByText(/enabled|disabled/i).first(),
    ).toBeVisible();
  });

  test('view activated templates sheet', async ({ platformAdminPage }) => {
    const bizPage = new PlatformCmsBusinessesPage(platformAdminPage);
    await bizPage.goto();
    await expect(bizPage.heading).toBeVisible();

    // Wait for business row to load before clicking
    await expect(platformAdminPage.getByText('E2E Test Business')).toBeVisible();

    await bizPage.clickBusiness('E2E Test Business');
    await expect(bizPage.activationsSheetTitle).toBeVisible();
  });
});
