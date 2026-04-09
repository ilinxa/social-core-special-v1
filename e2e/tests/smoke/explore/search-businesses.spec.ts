/**
 * Explore search businesses smoke tests.
 *
 * @layer L1
 * @system explore
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ExplorePage } from '../../../pages/explore/explore.page';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Search Businesses', () => {
  test('explore page renders with heading and search', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.heading).toBeVisible();
    await expect(explorePage.searchInput).toBeVisible();
  });

  test('businesses tab is visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.businessesTab).toBeVisible();
  });

  test('explore page accessible to anonymous users', async ({ page }) => {
    const explorePage = new ExplorePage(page);
    await explorePage.goto();

    await expect(explorePage.heading).toBeVisible();
    await expect(explorePage.searchInput).toBeVisible();
  });

  // --- Visual Regression ---
  test('explore page visual regression', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await expect(page).toHaveScreenshot('explore-page.png');
  });

  // --- Accessibility ---
  test('explore page has correct ARIA landmarks', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await checkLandmarks(page);
  });
});
