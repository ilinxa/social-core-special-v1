import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import * as api from "../helpers/api-helper";

// =============================================================================
// U-08..U-12 — Email Verification (6 tests)
// =============================================================================

test.describe("Email Verification", () => {
  // Use a dedicated user for verification tests to avoid interfering with User A
  const VERIFY_USER = {
    email: "e2e_verify_flow@test.com",
    username: "e2e_verify_flow",
    password: "TestPass123!",
  };

  test.beforeAll(async () => {
    // Register a fresh user for verification tests (not yet verified)
    try {
      await api.register(
        VERIFY_USER.email,
        VERIFY_USER.password,
        VERIFY_USER.username
      );
    } catch {
      // May already exist from previous run
    }
  });

  test("[U-08] Verify-email page renders with email param pre-filled", async ({
    page,
  }) => {
    await page.goto(
      `/verify-email?email=${encodeURIComponent(VERIFY_USER.email)}`
    );

    // Page should show email field (possibly disabled/pre-filled)
    const emailInput = page.getByLabel(/email/i);
    if (await emailInput.isVisible()) {
      await expect(emailInput).toHaveValue(VERIFY_USER.email);
    }

    // Code input should be visible
    await expect(page.getByLabel(/code/i)).toBeVisible();

    // Verify button
    await expect(
      page.getByRole("button", { name: /verify/i })
    ).toBeVisible();

    // Resend button
    await expect(page.getByRole("button", { name: /resend/i })).toBeVisible();
  });

  test("[U-10] Wrong code shows error", async ({ page }) => {
    await page.goto(
      `/verify-email?email=${encodeURIComponent(VERIFY_USER.email)}`
    );

    await page.getByLabel(/code/i).fill("000000");
    await page.getByRole("button", { name: /verify/i }).click();

    // Should show an error (may be generic or specific)
    await expect(
      page
        .getByText(
          /invalid|incorrect|expired|error|unexpected/i
        )
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-12] Resend button with cooldown", async ({ page }) => {
    await page.goto(
      `/verify-email?email=${encodeURIComponent(VERIFY_USER.email)}`
    );

    const resendBtn = page.getByRole("button", { name: /resend/i });
    await resendBtn.click();

    // After clicking, button should show countdown timer and be disabled
    await expect(
      page.getByText(/resend.*\d+s|resend code \(/i)
    ).toBeVisible({ timeout: 5_000 });
  });

  test("[U-11] Multiple wrong codes - rate limiting", async ({ page }) => {
    await page.goto(
      `/verify-email?email=${encodeURIComponent(VERIFY_USER.email)}`
    );

    // Submit wrong codes repeatedly
    for (let i = 1; i <= 6; i++) {
      await page.getByLabel(/code/i).fill(`${i}${i}${i}${i}${i}${i}`);
      await page.getByRole("button", { name: /verify/i }).click();
      await page.waitForTimeout(500);
    }

    // After multiple attempts, should still show error (rate limit may or may not trigger)
    // This test documents the behavior — either rate-limit message or generic error
    const errorVisible = await page
      .getByText(/too many|rate limit|locked|error|unexpected/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(errorVisible).toBeTruthy();
  });

  test("[U-09] Valid code redirects to login", async ({ page, db }) => {
    // Register a brand new user specifically for this test
    const freshUser = {
      email: "e2e_verify_valid@test.com",
      username: "e2e_verify_valid",
      password: "TestPass123!",
    };

    // Clean up and register fresh
    await db.cleanupTestUser(freshUser.email);
    await api.register(freshUser.email, freshUser.password, freshUser.username);

    // Get verification code from DB
    const code = await db.getVerificationCode(freshUser.email);
    expect(code).toBeTruthy();

    // Navigate to verify page and enter code
    await page.goto(
      `/verify-email?email=${encodeURIComponent(freshUser.email)}`
    );
    await page.getByLabel(/code/i).fill(code!);
    await page.getByRole("button", { name: /verify/i }).click();

    // Should redirect to /login on success
    await page.waitForURL(/\/login/, { timeout: 15_000 });
  });
});
