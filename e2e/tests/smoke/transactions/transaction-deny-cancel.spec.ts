/**
 * Transaction deny/cancel smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ActivityPage } from '../../../pages/transactions/transactions.page';

test.describe('Transaction Deny/Cancel', () => {
  test('activity page is accessible for deny/cancel operations', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    const activityPage = new ActivityPage(page);
    await activityPage.goto();

    // Deny/cancel buttons appear on transaction detail pages
    await expect(activityPage.heading).toBeVisible();
  });
});
