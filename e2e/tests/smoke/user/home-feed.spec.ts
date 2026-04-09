/**
 * Home feed smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P1, P3, P5
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { HomePage } from '../../../pages/user/home.page';

test.describe('Home Feed', () => {
  test('home page renders after login', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const homePage = new HomePage(page);
    await homePage.goto();

    await expect(homePage.heading).toBeVisible();
    await expect(homePage.welcomeText).toBeVisible();
  });

  test('sidebar navigation is visible on desktop', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const homePage = new HomePage(page);
    await homePage.goto();

    await expect(homePage.sidebarNav).toBeVisible();
    await expect(homePage.accountSwitcher).toBeVisible();
  });

  test('brand link navigates to home', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const homePage = new HomePage(page);
    await homePage.goto();

    await homePage.brandLink.click();
    await expect(page).toHaveURL(/\/home/);
  });
});
