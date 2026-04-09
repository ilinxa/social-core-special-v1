/**
 * Platform console dashboard smoke tests.
 *
 * @layer L1
 * @system platform
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformDashboardPage } from '../../../pages/platform/platform-console.page';

test.describe('Platform Console Dashboard', () => {
  test('dashboard renders for platform admin', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const dashboard = new PlatformDashboardPage(page);
    await dashboard.goto();

    await expect(dashboard.heading).toBeVisible();
  });

  test('sidebar navigation is visible', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const dashboard = new PlatformDashboardPage(page);
    await dashboard.goto();

    await expect(dashboard.sidebarNav).toBeVisible();
  });
});
