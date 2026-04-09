/**
 * Register smoke tests.
 *
 * @layer L1
 * @system auth
 * @parameters P1, P2, P5, P7
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { RegisterPage } from '../../../pages/auth/register.page';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';
import { checkFormLabels } from '../../../lib/a11y-checks';

test.describe('Register', () => {
  let registerPage: RegisterPage;

  test.beforeEach(async ({ page }) => {
    registerPage = new RegisterPage(page);
    await registerPage.goto();
  });

  test('renders registration form with all elements', async () => {
    await expect(registerPage.cardTitle).toBeVisible();
    await expect(registerPage.emailInput).toBeVisible();
    await expect(registerPage.usernameInput).toBeVisible();
    await expect(registerPage.passwordInput).toBeVisible();
    await expect(registerPage.confirmPasswordInput).toBeVisible();
    await expect(registerPage.submitButton).toBeVisible();
    await expect(registerPage.signInLink).toBeVisible();
  });

  test('successful registration redirects away from register', async ({ page }) => {
    const email = generateEmail('reg-smoke');
    const username = usernameFromEmail(email);
    await registerPage.register(email, username, 'TestPass123!');
    // Registration sets tokens → user is authenticated → auth layout redirects to /home
    // (or to /verify-email if unverified, but auth layout may redirect authenticated users)
    await expect(page).not.toHaveURL(/\/register/);
  });

  test('duplicate email shows error', async ({ page }) => {
    // Use an email that was already registered in global-setup
    await registerPage.register(
      'e2e-regular@test.com',
      'duplicate_user_test',
      'TestPass123!',
    );
    // Error shows as inline field error text (not form-level role="alert")
    await expect(
      page.getByText(/already registered|already taken|already exists|conflict/i),
    ).toBeVisible();
  });

  test('password mismatch shows error', async ({ page }) => {
    const email = generateEmail('reg-mismatch');
    const username = usernameFromEmail(email);
    await registerPage.registerWithDifferentPasswords(
      email,
      username,
      'TestPass123!',
      'DifferentPass456!',
    );
    // Form-level or field-level error about password mismatch
    const hasError = await page.getByText(/password.*match|do not match/i).isVisible();
    expect(hasError).toBe(true);
  });

  test('sign in link navigates correctly', async ({ page }) => {
    await registerPage.signInLink.click();
    await expect(page).toHaveURL(/\/login/);
  });

  // --- Visual Regression ---
  test('register page visual regression', async ({ page }) => {
    await expect(page).toHaveScreenshot('register-page.png');
  });

  // --- Accessibility ---
  test('register form inputs have associated labels', async ({ page }) => {
    const form = page.locator('form').first();
    await checkFormLabels(page, form);
  });
});
