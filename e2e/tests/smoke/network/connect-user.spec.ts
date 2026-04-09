/**
 * User connection smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P2, P3
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';

test.describe('Connect User', () => {
  test('connect button is visible on other user profile', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;

    // Navigate to another user's profile — button should appear for authenticated users
    // Username matches seeded data in global-setup (TEST_USERS.businessOwner.username)
    await page.goto('/users/e2e_bizowner');

    // Connect/Connected/Cancel Request button should be present
    await expect(
      page
        .getByRole('button', { name: /connect|connected|cancel request/i })
        .first(),
    ).toBeVisible();
  });
});
