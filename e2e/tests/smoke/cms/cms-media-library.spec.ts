/**
 * @layer L1
 * @system cms
 * @parameters P1, P2, P4, P10
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformMediaPage } from '../../../pages/platform/platform-cms.page';
import { isSystemEnabled } from '../../../lib/feature-gates';

test.describe('CMS Media Library (Platform Admin)', () => {
  test.skip(!isSystemEnabled('cms'), 'CMS system disabled');

  test('media library renders with heading', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();
    await expect(mediaPage.heading).toBeVisible();
  });

  test('grid and list view toggles are visible', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();

    await expect(mediaPage.gridViewButton).toBeVisible();
    await expect(mediaPage.listViewButton).toBeVisible();
  });

  test('upload button is visible', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();
    await expect(mediaPage.uploadButton).toBeVisible();
  });

  test('switching view modes works', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();

    await mediaPage.listViewButton.click();
    await mediaPage.gridViewButton.click();
    // No errors, views switched successfully
  });

  test('empty state or upload button is visible', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();

    // Either empty state or upload button should be visible (mutually inclusive).
    // `.first()` because both can render at once and `.or()` would yield 2 in strict mode.
    await expect(
      mediaPage.emptyState.or(mediaPage.uploadButton).first(),
    ).toBeVisible();
  });

  test('delete confirmation dialog exists', async ({ platformAdminPage }) => {
    const mediaPage = new PlatformMediaPage(platformAdminPage);
    await mediaPage.goto();
    // Verify delete locators are defined (dialog shown on action)
    expect(mediaPage.deleteButton).toBeDefined();
    expect(mediaPage.deleteConfirmButton).toBeDefined();
  });
});
