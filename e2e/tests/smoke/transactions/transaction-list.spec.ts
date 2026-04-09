/**
 * Transaction list (activity page) smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ActivityPage } from '../../../pages/transactions/transactions.page';

test.describe('Transaction List', () => {
  test('activity page renders with heading', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const activityPage = new ActivityPage(page);
    await activityPage.goto();

    await expect(activityPage.heading).toBeVisible();
  });

  test('role filter tabs are visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const activityPage = new ActivityPage(page);
    await activityPage.goto();

    await expect(activityPage.allTab).toBeVisible();
    await expect(activityPage.sentTab).toBeVisible();
    await expect(activityPage.receivedTab).toBeVisible();
  });

  test('shows transactions or empty state', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const activityPage = new ActivityPage(page);
    await activityPage.goto();

    // Should show either transactions or empty message
    await expect(
      activityPage.emptyMessage.or(
        activityPage.getCategoryHeading(/membership|ownership|social/i),
      ),
    ).toBeVisible();
  });
});
