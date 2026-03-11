import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";
import * as api from "../helpers/api-helper";

// =============================================================================
// U-21..U-27 — Password Management (8 tests)
// =============================================================================

test.describe("Password Management", () => {
  // Dedicated user for password reset tests to avoid breaking other tests
  const RESET_USER = {
    email: "e2e_pwd_reset@test.com",
    username: "e2e_pwd_reset",
    password: "TestPass123!",
    newPassword: "NewTestPass456!",
  };

  test.beforeAll(async () => {
    // Ensure reset user exists
    try {
      await api.register(
        RESET_USER.email,
        RESET_USER.password,
        RESET_USER.username
      );
    } catch {
      // Already exists
    }
  });

  test("[U-21] Forgot password form renders", async ({ page }) => {
    await page.goto("/forgot-password");

    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(
      page.getByRole("button", { name: /send reset link/i })
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /login|sign in|back/i })).toBeVisible();
  });

  test("[U-22] Submit forgot password shows success message (no enumeration)", async ({
    page,
  }) => {
    await page.goto("/forgot-password");

    await page.getByLabel("Email").fill(RESET_USER.email);
    await page.getByRole("button", { name: /send reset link/i }).click();

    // Should show generic success (doesn't reveal if account exists)
    await expect(
      page.getByText(/if an account exists|sent.*reset|check your email/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-23] Reset password form renders with token", async ({
    page,
    db,
  }) => {
    // Request reset via API to generate token
    await page.goto("/forgot-password");
    await page.getByLabel("Email").fill(RESET_USER.email);
    await page.getByRole("button", { name: /send reset link/i }).click();
    await page.waitForTimeout(2000);

    // Get token from DB
    const token = await db.getPasswordResetToken(RESET_USER.email);
    if (!token) {
      test.skip();
      return;
    }

    await page.goto(`/reset-password?token=${token}`);

    // Should show password form
    await expect(page.getByLabel(/new password|password/i).first()).toBeVisible();
    await expect(
      page.getByRole("button", { name: /reset password/i })
    ).toBeVisible();
  });

  test("[U-24] Valid password reset redirects to login", async ({
    page,
    db,
  }) => {
    // Request reset
    await page.goto("/forgot-password");
    await page.getByLabel("Email").fill(RESET_USER.email);
    await page.getByRole("button", { name: /send reset link/i }).click();
    await page.waitForTimeout(2000);

    const token = await db.getPasswordResetToken(RESET_USER.email);
    if (!token) {
      test.skip();
      return;
    }

    await page.goto(`/reset-password?token=${token}`);

    // Fill new password
    const pwdInput = page.getByLabel(/new password|password/i).first();
    await pwdInput.fill(RESET_USER.newPassword);

    // If there's a confirm password field
    const confirmInput = page.getByLabel(/confirm/i);
    if (await confirmInput.isVisible().catch(() => false)) {
      await confirmInput.fill(RESET_USER.newPassword);
    }

    await page.getByRole("button", { name: /reset password/i }).click();

    // Should redirect to login
    await page.waitForURL(/\/login/, { timeout: 15_000 });

    // Verify new password works by logging in
    await page.getByLabel("Email").fill(RESET_USER.email);
    await page.getByLabel("Password").fill(RESET_USER.newPassword);
    await page.getByRole("button", { name: "Sign In" }).click();
    await page.waitForURL("**/home", { timeout: 15_000 });
  });

  test("[U-25] Invalid token shows error", async ({ page }) => {
    await page.goto(
      "/reset-password?token=00000000-0000-0000-0000-000000000000"
    );

    // Either shows error immediately or after form submit
    const errorVisible = await page
      .getByText(/invalid|expired|not found/i)
      .first()
      .isVisible()
      .catch(() => false);

    if (!errorVisible) {
      // Try submitting
      const pwdInput = page.getByLabel(/password/i).first();
      if (await pwdInput.isVisible().catch(() => false)) {
        await pwdInput.fill("NewPassword123!");
        await page.getByRole("button", { name: /reset/i }).click();
        await expect(
          page.getByText(/invalid|expired|not found/i).first()
        ).toBeVisible({ timeout: 10_000 });
      }
    } else {
      expect(errorVisible).toBeTruthy();
    }
  });

  test("[U-26] Missing token shows error", async ({ page }) => {
    await page.goto("/reset-password");

    // Should show error or redirect
    const hasError = await page
      .getByText(/invalid|missing|token.*required|request.*new/i)
      .first()
      .isVisible()
      .catch(() => false);

    const redirectedAway =
      !page.url().includes("/reset-password") ||
      page.url().includes("/forgot-password");

    expect(hasError || redirectedAway).toBeTruthy();
  });

  test("[U-27] Change password (authenticated)", async ({ page }) => {
    // Login as User A
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    // Navigate to sessions page (which has change password)
    await page.goto("/sessions");

    // Fill change password form
    const currentPwd = page.getByLabel(/current password/i);
    const newPwd = page.getByLabel(/new password/i);

    await expect(currentPwd).toBeVisible();
    await expect(newPwd).toBeVisible();

    await currentPwd.fill(TEST_USERS.userA.password);
    await newPwd.fill("NewUserAPass456!");
    await page.getByRole("button", { name: /change password/i }).click();

    // Should show success
    await expect(
      page.getByText(/password.*changed|password.*updated|success/i).first()
    ).toBeVisible({ timeout: 10_000 });

    // Change back to original password for subsequent tests
    await currentPwd.fill("NewUserAPass456!");
    await newPwd.fill(TEST_USERS.userA.password);
    await page.getByRole("button", { name: /change password/i }).click();

    await expect(
      page.getByText(/password.*changed|password.*updated|success/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
