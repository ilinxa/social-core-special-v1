/**
 * Join request smoke tests.
 *
 * @layer L1
 * @system transactions
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Join Request', () => {
  test('request to join button visible on public profile', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    await page.goto(`/business/${E2E_BUSINESS.slug}`);

    // Join/Request to Join button should be visible for authenticated users
    await expect(
      page.getByRole('button', { name: /request to join|join/i }),
    ).toBeVisible();
  });

  test('requests list page renders for owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    await page.goto(`/bconsole/${E2E_BUSINESS.slug}/transactions/requests`);

    await expect(
      page.getByRole('heading', { level: 1, name: /requests/i }),
    ).toBeVisible();
  });
});
