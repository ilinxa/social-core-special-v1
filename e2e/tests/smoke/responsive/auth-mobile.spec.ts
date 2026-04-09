/**
 * Auth pages on mobile viewport (iPhone 14 Pro — 393x852).
 *
 * Verifies that login and register forms are fully usable on small screens:
 * all inputs visible, form submits work, links accessible.
 *
 * @layer L1
 * @system auth
 * @parameters P1 (Auth), P8 (Responsive)
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { LoginPage } from '../../../pages/auth/login.page';
import { RegisterPage } from '../../../pages/auth/register.page';
import { TEST_USERS } from '../../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';

test.describe('Auth — Mobile', () => {
  test('login form renders and all elements are visible', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await expect(loginPage.cardTitle).toBeVisible();
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
    await expect(loginPage.forgotPasswordLink).toBeVisible();
    await expect(loginPage.signUpLink).toBeVisible();
  });

  test('login form is usable — fields accept input and submit works', async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Type into fields — verify they accept input on mobile
    await loginPage.emailInput.fill(TEST_USERS.regular.email);
    await expect(loginPage.emailInput).toHaveValue(TEST_USERS.regular.email);

    await loginPage.passwordInput.fill(TEST_USERS.regular.password);
    await expect(loginPage.passwordInput).toHaveValue(TEST_USERS.regular.password);

    // Submit
    await loginPage.submitButton.click();
    await expect(page).toHaveURL(/\/home/);
  });

  test('register form renders all fields on mobile', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();

    await expect(registerPage.cardTitle).toBeVisible();
    await expect(registerPage.emailInput).toBeVisible();
    await expect(registerPage.usernameInput).toBeVisible();
    await expect(registerPage.passwordInput).toBeVisible();
    await expect(registerPage.confirmPasswordInput).toBeVisible();
    await expect(registerPage.submitButton).toBeVisible();
    await expect(registerPage.signInLink).toBeVisible();
  });

  test('register form is usable — submit redirects to verify', async ({
    page,
  }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();

    const email = generateEmail('mobile-reg');
    const username = usernameFromEmail(email);

    await registerPage.register(email, username, 'TestPass123!');
    await expect(page).toHaveURL(/\/verify-email/);
  });

  test('forgot password link is tappable on mobile', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.forgotPasswordLink.click();
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test('sign up link navigates from login on mobile', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.signUpLink.click();
    await expect(page).toHaveURL(/\/register/);
  });
});
