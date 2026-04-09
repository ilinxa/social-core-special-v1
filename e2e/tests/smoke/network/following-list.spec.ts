/**
 * Following list smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { MyNetworkPage } from '../../../pages/network/network.page';

test.describe('Following List', () => {
  test('following tab shows content', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    await networkPage.followingTab.click();

    // Should show either following items or empty state
    await expect(
      networkPage.notFollowingMessage.or(
        page.getByRole('button', { name: /unfollow/i }).first(),
      ),
    ).toBeVisible();
  });
});
