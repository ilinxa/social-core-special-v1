/**
 * Platform transactions smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformTransactionsDashboardPage } from '../../../pages/platform/platform-transactions.page';

test.describe('Platform Transactions', () => {
  test('transactions dashboard renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const txPage = new PlatformTransactionsDashboardPage(page);
    await txPage.goto();

    await expect(txPage.heading).toBeVisible();
  });

  test('transactions dashboard shows request and invitation cards', async ({
    platformAdminPage,
  }) => {
    const page = platformAdminPage;
    const txPage = new PlatformTransactionsDashboardPage(page);
    await txPage.goto();

    await expect(txPage.requestsCard).toBeVisible();
    await expect(txPage.invitationsCard).toBeVisible();
  });
});
