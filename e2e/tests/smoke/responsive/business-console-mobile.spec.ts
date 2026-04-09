/**
 * Business console on mobile viewport (iPhone 14 Pro — 393x852).
 *
 * Verifies that the business console adapts on small screens:
 * sidebar collapses, main content fills viewport, key actions accessible.
 *
 * @layer L1
 * @system business
 * @parameters P2 (Navigation), P8 (Responsive)
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BasePage } from '../../../pages/base.page';
import { BusinessDashboardPage, BusinessSettingsPage } from '../../../pages/business/business-console.page';
import { E2E_BUSINESS, TEST_USERS } from '../../../lib/constants';

test.describe('Business Console — Mobile', () => {
  test.beforeEach(async ({ page }) => {
    // Login as business owner
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.businessOwner.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.businessOwner.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/(home|dashboard|activity)/);
  });

  test('dashboard renders on mobile', async ({ page }) => {
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.heading).toBeVisible();
    await expect(dashboard.main).toBeVisible();
  });

  test('sidebar is hidden on mobile in business console', async ({ page }) => {
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    // Desktop sidebar should be hidden
    await expect(dashboard.sidebarNav).toBeHidden();
  });

  test('bottom navbar shows in business console', async ({ page }) => {
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    // Mobile bottom navbar should be present
    await expect(dashboard.bottomNavbar).toBeVisible();
  });

  test('settings page renders on mobile', async ({ page }) => {
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    await expect(settingsPage.heading).toBeVisible();
  });

  test('danger zone buttons are visible on mobile settings', async ({
    page,
  }) => {
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    // Transfer ownership and archive buttons should be reachable on mobile
    await expect(settingsPage.transferOwnershipButton).toBeVisible();
    await expect(settingsPage.archiveButton).toBeVisible();
  });

  test('account switcher works on mobile', async ({ page }) => {
    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    // Account switcher should be accessible
    if (await dashboard.accountSwitcher.isVisible()) {
      await dashboard.accountSwitcher.click();
      // Should show Personal option
      await expect(page.getByText('Personal').first()).toBeVisible();
    }
  });
});
