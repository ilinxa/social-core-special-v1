/**
 * Transaction pages smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import {
  BusinessTransactionsDashboardPage,
} from '../../../pages/business/business-transactions.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Transaction Pages', () => {
  test('business transactions dashboard renders with all cards', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessTransactionsDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.heading).toBeVisible();
    await expect(dashboard.requestsCard).toBeVisible();
    await expect(dashboard.invitationsCard).toBeVisible();
    await expect(dashboard.settingsCard).toBeVisible();
  });

  test('requests page status filters are visible', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    await page.goto(`/bconsole/${E2E_BUSINESS.slug}/transactions/requests`);

    await expect(page.getByRole('button', { name: /^all$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /^pending$/i })).toBeVisible();
  });
});
