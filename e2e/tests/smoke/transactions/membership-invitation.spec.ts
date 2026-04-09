/**
 * Membership invitation smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import {
  BusinessTransactionsDashboardPage,
  TransactionListPage,
} from '../../../pages/business/business-transactions.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Membership Invitation', () => {
  test('invitations page renders from dashboard', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new BusinessTransactionsDashboardPage(page);
    await dashboard.goto(E2E_BUSINESS.slug);

    await expect(dashboard.invitationsCard).toBeVisible();
  });

  test('invitations list page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    await page.goto(`/bconsole/${E2E_BUSINESS.slug}/transactions/invitations`);

    await expect(
      page.getByRole('heading', { level: 1, name: /invitations/i }),
    ).toBeVisible();
  });
});
