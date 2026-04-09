/**
 * Profile view smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P1, P4
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ProfileViewPage } from '../../../pages/user/profile.page';
import { checkLandmarks } from '../../../lib/a11y-checks';

test.describe('Profile View', () => {
  test('own profile renders with key elements', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();

    await expect(profilePage.heading).toBeVisible();
    await expect(profilePage.editButton).toBeVisible();
    await expect(profilePage.displayName).toBeVisible();
    await expect(profilePage.username).toBeVisible();
  });

  test('profile shows avatar area', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();

    // Wait for profile data to load before checking avatar
    await expect(profilePage.heading).toBeVisible();
    await expect(profilePage.avatar).toBeVisible();
  });

  test('edit button navigates to edit page', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();

    await profilePage.clickEdit();
    await expect(page).toHaveURL(/\/profile\/edit/);
  });

  // --- Visual Regression ---
  test('profile page visual regression', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();
    await expect(page).toHaveScreenshot('profile-view.png');
  });

  // --- Accessibility ---
  test('profile page has correct ARIA landmarks', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();
    await checkLandmarks(page);
  });
});
