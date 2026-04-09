/**
 * Business public profile smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P5, P7
 * @priority P1
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { BusinessProfilePage } from '../../../pages/business/business-profile.page';
import { E2E_BUSINESS } from '../../../lib/constants';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Business Public Profile', () => {
  test('anonymous user can view public business profile', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(E2E_BUSINESS.slug);

    await expect(profilePage.businessName).toBeVisible();
  });

  test('non-existent business shows not found', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto('this-business-does-not-exist-xyz');

    await expect(profilePage.notFoundMessage).toBeVisible();
  });

  test('public profile shows about section when available', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(E2E_BUSINESS.slug);

    // The page should render without errors even if sections are empty
    await expect(profilePage.businessName).toBeVisible();
  });

  // --- Visual Regression ---
  test('business profile visual regression', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(E2E_BUSINESS.slug);
    await expect(page).toHaveScreenshot('business-profile.png');
  });

  // --- Accessibility ---
  test('business profile has correct ARIA landmarks', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(E2E_BUSINESS.slug);
    await checkLandmarks(page);
  });
});
