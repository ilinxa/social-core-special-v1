/**
 * Explore filters smoke tests.
 *
 * @layer L1
 * @system explore
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ExplorePage } from '../../../pages/explore/explore.page';

test.describe('Explore Filters', () => {
  test('filters button is visible on businesses tab', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    // Filters button is hidden on the "All" tab — switch to Businesses tab
    await explorePage.businessesTab.click();
    await expect(explorePage.filtersButton).toBeVisible();
  });

  test('subheading describes the explore page', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.subheading).toBeVisible();
  });
});
