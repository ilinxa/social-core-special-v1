/**
 * Explore search users smoke tests.
 *
 * @layer L1
 * @system explore
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ExplorePage } from '../../../pages/explore/explore.page';

test.describe('Search Users', () => {
  test('users tab visible for authenticated users', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.usersTab).toBeVisible();
  });

  test('all tab is selected by default', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.allTab).toBeVisible();
  });
});
