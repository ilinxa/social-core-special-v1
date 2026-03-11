import { type Page, expect } from "@playwright/test";

// =============================================================================
// AUTH HELPER — Browser-based login/registration helpers
// =============================================================================

/**
 * Login via the UI login form. Waits for redirect to /home.
 */
export async function loginViaUI(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL("**/home", { timeout: 15_000 });
}

/**
 * Login via the UI and return. Does NOT assert redirect target.
 */
export async function loginViaUINoRedirectCheck(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  // Wait for navigation away from /login
  await expect(page).not.toHaveURL(/\/login/);
}

/**
 * Logout via the user menu dropdown.
 */
export async function logoutViaUI(page: Page): Promise<void> {
  // Open user menu in topbar
  await page.getByTestId("user-menu-trigger").click();
  await page.getByRole("menuitem", { name: "Sign Out" }).click();
  await page.waitForURL("**/login", { timeout: 10_000 });
}

/**
 * Assert that we're on the login page (auth guard redirected us).
 */
export async function expectRedirectedToLogin(page: Page): Promise<void> {
  await expect(page).toHaveURL(/\/login/);
}
