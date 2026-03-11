import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";

// =============================================================================
// U-01..U-07 — Registration (9 tests)
// =============================================================================

test.describe("Registration", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/register");
  });

  test("[U-01] Registration form renders correctly", async ({ page }) => {
    // Core form fields
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm Password")).toBeVisible();

    // Submit button
    await expect(
      page.getByRole("button", { name: "Create Account" })
    ).toBeVisible();

    // OAuth buttons
    await expect(page.getByRole("button", { name: /google/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /apple/i })).toBeVisible();

    // Login link
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
  });

  test("[U-02] Valid registration redirects to verify-email", async ({
    page,
  }) => {
    const user = TEST_USERS.fresh;

    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByLabel("Confirm Password").fill(user.password);
    await page.getByRole("button", { name: "Create Account" }).click();

    await page.waitForURL(/\/verify-email/, { timeout: 15_000 });
    expect(page.url()).toContain("verify-email");
  });

  test("[U-03] Duplicate email shows error", async ({ page }) => {
    const taken = TEST_USERS.taken;

    await page.getByLabel("Email").fill(taken.email);
    await page.getByLabel("Username").fill("unique_username_xyz");
    await page.getByLabel("Password", { exact: true }).fill(taken.password);
    await page.getByLabel("Confirm Password").fill(taken.password);
    await page.getByRole("button", { name: "Create Account" }).click();

    // Wait for error message about duplicate email
    await expect(
      page.getByText(/already registered|already exists|email.*taken/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-04] Duplicate username shows error", async ({ page }) => {
    const taken = TEST_USERS.taken;

    await page.getByLabel("Email").fill("unique_email_xyz@test.com");
    await page.getByLabel("Username").fill(taken.username);
    await page.getByLabel("Password", { exact: true }).fill(taken.password);
    await page.getByLabel("Confirm Password").fill(taken.password);
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(
      page.getByText(/already taken|username.*exists|username.*taken/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-05] Weak password (too short) shows validation error", async ({
    page,
  }) => {
    await page.getByLabel("Password", { exact: true }).fill("1234567");
    await page.getByLabel("Confirm Password").fill("1234567");
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(
      page.getByText(/at least 8 characters|too short|minimum.*8/i)
    ).toBeVisible();
  });

  test("[U-05b] Weak password (no uppercase) shows validation error", async ({
    page,
  }) => {
    await page.getByLabel("Password", { exact: true }).fill("testpass123!");
    await page.getByLabel("Confirm Password").fill("testpass123!");
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(
      page.getByText(/uppercase|capital letter/i)
    ).toBeVisible();
  });

  test("[U-06] Empty submit shows validation errors on all fields", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Create Account" }).click();

    // Should show at least error indicators for required fields
    const errors = page.locator(".text-destructive, [role='alert']");
    await expect(errors.first()).toBeVisible();
  });

  test("[U-07] Invalid email format shows validation error", async ({
    page,
  }) => {
    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Username").fill("valid_user");
    await page.getByLabel("Password", { exact: true }).fill("TestPass123!");
    await page.getByLabel("Confirm Password").fill("TestPass123!");
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(
      page.getByText(/valid email|invalid email/i)
    ).toBeVisible();
  });

  test("[U-02b] Register User A for subsequent tests", async ({ page, db }) => {
    // This test creates User A which is used throughout the rest of the suite.
    // First clean up any existing User A
    await db.cleanupTestUser(TEST_USERS.userA.email);

    const user = TEST_USERS.userA;
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByLabel("Confirm Password").fill(user.password);
    await page.getByRole("button", { name: "Create Account" }).click();

    await page.waitForURL(/\/verify-email/, { timeout: 15_000 });

    // Verify via DB and confirm
    const code = await db.getVerificationCode(user.email);
    expect(code).toBeTruthy();

    // Navigate to verify page and enter code
    await page.goto(`/verify-email?email=${encodeURIComponent(user.email)}`);
    await page.getByLabel(/code/i).fill(code!);
    await page.getByRole("button", { name: /verify/i }).click();

    await page.waitForURL(/\/login/, { timeout: 15_000 });
  });
});
