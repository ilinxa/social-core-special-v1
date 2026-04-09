/**
 * Business console dashboard smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessDashboardPage } from '../../../pages/business/business-console.page';
import { E2E_BUSINESS } from '../../../lib/constants';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Business Console Dashboard', () => {
  test('dashboard renders for business owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.heading).toBeVisible();
  });

  test('sidebar navigation links are visible in console', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.sidebarNav).toBeVisible();
  });

  test('account switcher shows business context', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.accountSwitcher).toBeVisible();
  });

  // --- Visual Regression ---
  test('business dashboard visual regression', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);
    await expect(page).toHaveScreenshot('business-dashboard.png');
  });

  // --- Accessibility ---
  test('business dashboard has correct ARIA landmarks', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);
    await checkLandmarks(page);
  });
});
