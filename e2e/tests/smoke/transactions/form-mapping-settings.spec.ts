/**
 * Transaction form mapping settings smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { TransactionSettingsPage } from '../../../pages/transactions/transactions.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Form Mapping Settings', () => {
  test('transaction settings page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new TransactionSettingsPage(page);
    await settingsPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(settingsPage.heading).toBeVisible();
  });

  test('settings page shows description', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const settingsPage = new TransactionSettingsPage(page);
    await settingsPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(settingsPage.description).toBeVisible();
  });
});
