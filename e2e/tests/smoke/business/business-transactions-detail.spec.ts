/**
 * Business transactions smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessTransactionsDashboardPage } from '../../../pages/business/business-transactions.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Transactions', () => {
  test('transactions dashboard renders with cards', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const txPage = new BusinessTransactionsDashboardPage(page);
    await txPage.goto(E2E_BUSINESS.slug);

    await expect(txPage.heading).toBeVisible();
    await expect(txPage.requestsCard).toBeVisible();
    await expect(txPage.invitationsCard).toBeVisible();
  });

  test('requests list page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    await page.goto(`/bconsole/${E2E_BUSINESS.slug}/transactions/requests`);

    await expect(page.getByRole('heading', { level: 1, name: /requests/i })).toBeVisible();
  });

  test('invitations list page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    await page.goto(`/bconsole/${E2E_BUSINESS.slug}/transactions/invitations`);

    await expect(
      page.getByRole('heading', { level: 1, name: /invitations/i }),
    ).toBeVisible();
  });
});
