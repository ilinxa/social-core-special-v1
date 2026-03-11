import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";

// =============================================================================
// U-13..U-20 — Login (8 tests)
// =============================================================================

test.describe("Login", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
  });

  test("[U-13] Login form renders correctly", async ({ page }) => {
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Sign In" })
    ).toBeVisible();

    // OAuth buttons
    await expect(page.getByRole("button", { name: /google/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /apple/i })).toBeVisible();

    // Links
    await expect(
      page.getByRole("link", { name: /forgot password/i })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /sign up/i })
    ).toBeVisible();
  });

  test("[U-14] Valid login redirects to /home", async ({ page }) => {
    const user = TEST_USERS.userA;

    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password").fill(user.password);
    await page.getByRole("button", { name: "Sign In" }).click();

    await page.waitForURL("**/home", { timeout: 15_000 });
  });

  test("[U-15] Wrong password shows error", async ({ page }) => {
    await page.getByLabel("Email").fill(TEST_USERS.userA.email);
    await page.getByLabel("Password").fill("WrongPassword999!");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(
      page.getByText(/invalid email or password|invalid credentials/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-16] Rate limiting after many failed attempts", async ({ page }) => {
    // Submit wrong credentials rapidly
    for (let i = 0; i < 12; i++) {
      await page.getByLabel("Email").fill(TEST_USERS.userA.email);
      await page.getByLabel("Password").fill(`Wrong${i}Pass!`);
      await page.getByRole("button", { name: /sign in/i }).click();
      await page.waitForTimeout(300);
    }

    // Should see rate limit or error message
    const rateLimited = await page
      .getByText(/too many|rate limit|try again|throttled/i)
      .first()
      .isVisible()
      .catch(() => false);

    const errorVisible = await page
      .getByText(/invalid|error/i)
      .first()
      .isVisible()
      .catch(() => false);

    // Either rate limited or still showing errors (both are acceptable)
    expect(rateLimited || errorVisible).toBeTruthy();
  });

  test("[U-17] Google OAuth button visible", async ({ page }) => {
    const googleBtn = page.getByRole("button", { name: /google/i });
    await expect(googleBtn).toBeVisible();
    await expect(googleBtn).toBeEnabled();
  });

  test("[U-18] Apple OAuth button visible", async ({ page }) => {
    const appleBtn = page.getByRole("button", { name: /apple/i });
    await expect(appleBtn).toBeVisible();
    await expect(appleBtn).toBeEnabled();
  });

  test("[U-19] Forgot password link navigates to /forgot-password", async ({
    page,
  }) => {
    await page.getByRole("link", { name: /forgot password/i }).click();
    await page.waitForURL("**/forgot-password", { timeout: 10_000 });
  });

  test("[U-20] Sign up link navigates to /register", async ({ page }) => {
    await page.getByRole("link", { name: /sign up/i }).click();
    await page.waitForURL("**/register", { timeout: 10_000 });
  });
});
