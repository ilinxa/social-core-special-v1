/**
 * Ownership transfer smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessSettingsPage } from '../../../pages/business/business-console.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Ownership Transfer', () => {
  test('transfer ownership button visible in settings', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(E2E_BUSINESS.slug);

    await expect(settingsPage.transferOwnershipButton).toBeVisible();
  });
});
