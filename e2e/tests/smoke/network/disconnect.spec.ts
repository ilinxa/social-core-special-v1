/**
 * Disconnect user smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { MyNetworkPage } from '../../../pages/network/network.page';

test.describe('Disconnect', () => {
  test('network page is accessible for disconnect operations', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    // Disconnect buttons appear on connection cards
    await expect(networkPage.heading).toBeVisible();
  });
});
