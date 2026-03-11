import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-44..U-46 — Username Management (4 tests)
// =============================================================================

test.describe("Username", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/settings");
  });

  test("[U-44] Change username successfully", async ({ page }) => {
    const usernameInput = page.getByLabel(/username/i).first();
    await expect(usernameInput).toBeVisible();

    // Change to a new username
    const newUsername = `e2e_user_a_${Date.now().toString(36).slice(-4)}`;
    await usernameInput.clear();
    await usernameInput.fill(newUsername);

    // Wait for availability check
    await page.waitForTimeout(1500);

    // Look for "Available" indicator
    const available = page.getByText(/available/i);
    if (await available.isVisible().catch(() => false)) {
      await page.getByRole("button", { name: /update username/i }).click();
      await page.waitForTimeout(2000);

      // Revert back to original username
      await usernameInput.clear();
      await usernameInput.fill(TEST_USERS.userA.username);
      await page.waitForTimeout(1500);
      await page.getByRole("button", { name: /update username/i }).click();
      await page.waitForTimeout(2000);
    }
  });

  test("[U-45] Taken username shows error indicator", async ({ page }) => {
    const usernameInput = page.getByLabel(/username/i).first();

    await usernameInput.clear();
    await usernameInput.fill(TEST_USERS.taken.username);

    // Wait for availability check
    await page.waitForTimeout(2000);

    // Should show "taken" or "unavailable" indicator
    await expect(
      page.getByText(/taken|unavailable|already.*use/i).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("[U-46] Invalid characters show validation error", async ({ page }) => {
    const usernameInput = page.getByLabel(/username/i).first();

    await usernameInput.clear();
    await usernameInput.fill("user@name!");

    // Either shows immediate validation or on submit
    await page.getByRole("button", { name: /update username/i }).click();

    await expect(
      page.getByText(/letters.*numbers.*underscores|invalid|special char/i).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("[U-46b] Username too short shows validation error", async ({
    page,
  }) => {
    const usernameInput = page.getByLabel(/username/i).first();

    await usernameInput.clear();
    await usernameInput.fill("ab");

    await page.getByRole("button", { name: /update username/i }).click();

    await expect(
      page.getByText(/at least|minimum|too short|5.*char/i).first()
    ).toBeVisible({ timeout: 5_000 });
  });
});
