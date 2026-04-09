/**
 * Platform businesses management smoke tests.
 *
 * @layer L1
 * @system platform
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformBusinessesPage } from '../../../pages/platform/platform-console.page';

test.describe('Platform Businesses', () => {
  test('businesses page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const bizPage = new PlatformBusinessesPage(page);
    await bizPage.goto();

    await expect(bizPage.heading).toBeVisible();
  });

  test('shows coming soon placeholder', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const bizPage = new PlatformBusinessesPage(page);
    await bizPage.goto();

    await expect(bizPage.placeholderText).toBeVisible();
  });
});
