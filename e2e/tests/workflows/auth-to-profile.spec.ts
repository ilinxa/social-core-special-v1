/**
 * W1: Auth → Profile workflow.
 *
 * Verifies that a user can log in, land on the home page, navigate to their
 * profile, and persist their session across page reloads and internal navigation.
 *
 * @layer L2
 * @system auth, users
 * @parameters P1 (Auth), P2 (Navigation), P3 (Session)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { TEST_USERS } from '../../lib/constants';
import { LoginPage } from '../../pages/auth/login.page';
import { HomePage } from '../../pages/user/home.page';
import { ProfileViewPage } from '../../pages/user/profile.page';

test.describe('W1: Login → Home → Profile', () => {
  test('user can login, view home, navigate to profile, and session persists', async ({
    page,
  }) => {
    // Step 1 — Navigate to /login
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await expect(loginPage.cardTitle).toBeVisible();

    // Step 2 — Login with pre-built regular user credentials
    await loginPage.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    // Step 3 — Expect redirect to /home
    await page.waitForURL(/\/home/);

    // Step 4 — Verify home page heading visible
    const homePage = new HomePage(page);
    await expect(homePage.heading).toBeVisible();

    // Step 5 — Navigate to /profile
    const profilePage = new ProfileViewPage(page);
    await profilePage.goto();
    await expect(profilePage.heading).toBeVisible();

    // Step 6 — Verify profile renders with user's username
    await expect(page.getByText(`@${TEST_USERS.regular.username}`)).toBeVisible();

    // Step 7 — Refresh page → verify still authenticated (session persistence)
    await page.reload();
    await expect(profilePage.heading).toBeVisible();
    await expect(page.getByText(`@${TEST_USERS.regular.username}`)).toBeVisible();

    // Step 8 — Navigate to /home via sidebar → verify loads without re-login
    await homePage.clickSidebarLink('Home');
    await page.waitForURL(/\/home/);
    await expect(homePage.heading).toBeVisible();
  });
});
