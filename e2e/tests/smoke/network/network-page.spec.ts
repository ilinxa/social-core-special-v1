/**
 * User network page smoke tests.
 *
 * @layer L1
 * @system network
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { MyNetworkPage } from '../../../pages/network/network.page';

test.describe('Network Page', () => {
  test('network page renders with heading', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    await expect(networkPage.heading).toBeVisible();
  });

  test('connections and following tabs are visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    await expect(networkPage.connectionsTab).toBeVisible();
    await expect(networkPage.followingTab).toBeVisible();
  });

  test('search input is visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const networkPage = new MyNetworkPage(page);
    await networkPage.goto();

    await expect(networkPage.searchInput).toBeVisible();
  });
});
