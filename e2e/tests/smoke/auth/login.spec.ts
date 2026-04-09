/**
 * Login smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P1, P2, P5, P7
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { LoginPage } from '../../../pages/auth/login.page';
import { TEST_USERS } from '../../../lib/constants';
import { checkLandmarks, checkFormLabels } from '../../../lib/a11y-checks';

test.describe('Login', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('renders login form with all elements', async () => {
    await expect(loginPage.cardTitle).toBeVisible();
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
    await expect(loginPage.forgotPasswordLink).toBeVisible();
    await expect(loginPage.signUpLink).toBeVisible();
  });

  test('successful login redirects to home', async ({ page }) => {
    const { email, password } = TEST_USERS.regular;
    await loginPage.login(email, password);
    await expect(page).toHaveURL(/\/home/);
  });

  test('invalid credentials show error', async () => {
    await loginPage.login('wrong@example.com', 'WrongPass123!');
    await expect(loginPage.formError).toBeVisible();
    await expect(loginPage.formError).toContainText(/invalid/i);
  });

  test('empty email shows validation error', async () => {
    await loginPage.passwordInput.fill('SomePass123!');
    await loginPage.submitButton.click();
    // Email field should show browser or form validation
    await expect(loginPage.emailInput).toHaveAttribute('aria-invalid', 'true');
  });

  test('empty password shows validation error', async () => {
    await loginPage.emailInput.fill('test@example.com');
    await loginPage.submitButton.click();
    await expect(loginPage.passwordInput).toHaveAttribute('aria-invalid', 'true');
  });

  test('forgot password link navigates correctly', async ({ page }) => {
    await loginPage.forgotPasswordLink.click();
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test('sign up link navigates correctly', async ({ page }) => {
    await loginPage.signUpLink.click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('shows verified banner when redirected from verification', async ({ page }) => {
    await page.goto('/login?verified=true');
    loginPage = new LoginPage(page);
    await expect(loginPage.verifiedMessage).toBeVisible();
    await expect(loginPage.verifiedMessage).toContainText(/verified/i);
  });

  // --- Visual Regression ---
  test('login page visual regression', async ({ page }) => {
    await expect(page).toHaveScreenshot('login-page.png');
  });

  // --- Accessibility ---
  test('login form inputs have associated labels', async ({ page }) => {
    const form = page.locator('form').first();
    await checkFormLabels(page, form);
  });
});
