/**
 * Business settings smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessSettingsPage } from '../../../pages/business/business-console.page';
import { E2E_BUSINESS } from '../../../lib/constants';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Business Settings', () => {
  test('settings page renders for owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    await expect(settingsPage.heading).toBeVisible();
  });

  test('danger zone with transfer ownership is visible for owner', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    await expect(settingsPage.transferOwnershipButton).toBeVisible();
  });

  test('archive button is visible for owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    await expect(settingsPage.archiveButton).toBeVisible();
  });

  // --- Visual Regression ---
  test('business settings visual regression', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);
    await expect(page).toHaveScreenshot('business-settings.png');
  });

  // --- Accessibility ---
  test('business settings has correct ARIA landmarks', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);
    await checkLandmarks(page);
  });
});
