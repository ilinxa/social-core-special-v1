import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-97..U-99 — Account Deactivation (4 tests)
// =============================================================================
// Uses dedicated e2e_deactivate user (consumed — not reusable after U-99).

test.describe("Account Deactivation", () => {
  test("[U-97] Deactivation dialog renders", async ({ page }) => {
    await loginViaUI(
      page,
      TEST_USERS.deactivate.email,
      TEST_USERS.deactivate.password
    );
    await page.goto("/settings");

    // Click the "Deactivate" button in Danger Zone
    await page.getByRole("button", { name: "Deactivate" }).click();

    // Dialog should open
    await expect(
      page.getByText(/deactivate your account/i)
    ).toBeVisible({ timeout: 5_000 });

    // Confirmation input
    await expect(
      page.getByPlaceholder(/type.*deactivate.*confirm/i)
    ).toBeVisible();

    // Deactivate Account button should be disabled
    const deactivateBtn = page.getByRole("button", {
      name: "Deactivate Account",
    });
    await expect(deactivateBtn).toBeDisabled();
  });

  test("[U-98] Button enables only with 'deactivate' typed", async ({
    page,
  }) => {
    await loginViaUI(
      page,
      TEST_USERS.deactivate.email,
      TEST_USERS.deactivate.password
    );
    await page.goto("/settings");

    await page.getByRole("button", { name: "Deactivate" }).click();

    const confirmInput = page.getByPlaceholder(/type.*deactivate.*confirm/i);
    const deactivateBtn = page.getByRole("button", {
      name: "Deactivate Account",
    });

    // Type partial text — button should stay disabled
    await confirmInput.fill("deactiv");
    await expect(deactivateBtn).toBeDisabled();

    // Type full "deactivate" — button should enable
    await confirmInput.fill("deactivate");
    await expect(deactivateBtn).toBeEnabled();

    // Cancel instead of confirming (preserve the user for U-99)
    await page.getByRole("button", { name: "Cancel" }).click();
  });

  test("[U-99] Deactivation logs out and login fails", async ({ page }) => {
    await loginViaUI(
      page,
      TEST_USERS.deactivate.email,
      TEST_USERS.deactivate.password
    );
    await page.goto("/settings");

    // Open dialog and confirm deactivation
    await page.getByRole("button", { name: "Deactivate" }).click();
    await page.getByPlaceholder(/type.*deactivate.*confirm/i).fill("deactivate");
    await page.getByRole("button", { name: "Deactivate Account" }).click();

    // Should redirect to /login
    await page.waitForURL(/\/login/, { timeout: 15_000 });

    // Try to login with deactivated account
    await page.getByLabel("Email").fill(TEST_USERS.deactivate.email);
    await page.getByLabel("Password").fill(TEST_USERS.deactivate.password);
    await page.getByRole("button", { name: "Sign In" }).click();

    // Should show deactivated account error
    await expect(
      page.getByText(/deactivated|disabled|inactive/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
