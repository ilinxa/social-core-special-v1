/**
 * Follow business smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P2, P3
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Follow Business', () => {
  test('follow button is visible on public business profile', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    await page.goto(`/business/${E2E_BUSINESS.slug}`);

    await expect(page.getByRole('button', { name: /follow/i })).toBeVisible();
  });

  test('anonymous user does not see follow button', async ({ page }) => {
    await page.goto(`/business/${E2E_BUSINESS.slug}`);

    // Follow button should not be visible for unauthenticated users
    await expect(page.getByRole('button', { name: /^follow$/i })).not.toBeVisible();
  });
});
