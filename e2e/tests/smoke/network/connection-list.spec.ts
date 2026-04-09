/**
 * Connection list smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { MyNetworkPage } from '../../../pages/network/network.page';

test.describe('Connection List', () => {
  test('connections tab shows content', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    // Connections tab is default active
    await expect(
      networkPage.noConnectionsMessage.or(
        page.getByRole('button', { name: /disconnect/i }).first(),
      ),
    ).toBeVisible();
  });
});
