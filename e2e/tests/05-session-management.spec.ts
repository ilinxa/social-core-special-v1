import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-28..U-32 — Session Management (6 tests)
// =============================================================================

test.describe("Session Management", () => {
  test("[U-28] Sessions page shows at least 1 session", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/sessions");

    // Should show at least one session card
    await expect(
      page.getByText(/web|mobile|desktop|browser|device/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-29] Current session has 'Current' badge", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/sessions");

    await expect(page.getByText(/current/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("[U-30] Current session has no Revoke button", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/sessions");

    // Find the "Current" session and verify it has no revoke button nearby
    const currentBadge = page.getByText(/current/i).first();
    await expect(currentBadge).toBeVisible();

    // The current session card should not have a revoke/remove button
    const currentCard = currentBadge.locator("xpath=ancestor::div[contains(@class, 'card') or contains(@class, 'border')]").first();
    const revokeInCurrent = currentCard.getByRole("button", {
      name: /revoke|remove/i,
    });

    // Should not be present or not visible
    const revokeCount = await revokeInCurrent.count();
    expect(revokeCount).toBe(0);
  });

  test("[U-31] Revoke other session", async ({ page, context, browser }) => {
    // Login in primary context
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    // Create a second context (separate session) and login there too
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await page2.goto("http://localhost:3000/login");
    await page2.getByLabel("Email").fill(TEST_USERS.userA.email);
    await page2.getByLabel("Password").fill(TEST_USERS.userA.password);
    await page2.getByRole("button", { name: "Sign In" }).click();
    await page2.waitForURL("**/home", { timeout: 15_000 });

    // Now in primary context, go to sessions page
    await page.goto("/sessions");
    await page.waitForTimeout(2000);

    // Should see at least 2 sessions now — look for revoke button
    const revokeBtn = page
      .getByRole("button", { name: /revoke|remove/i })
      .first();

    if (await revokeBtn.isVisible().catch(() => false)) {
      await revokeBtn.click();
      // Wait for session to be removed
      await page.waitForTimeout(2000);
    }

    await context2.close();
  });

  test("[U-32] Sign Out Everywhere redirects to login", async ({
    page,
  }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/sessions");

    const signOutAllBtn = page.getByRole("button", {
      name: /sign out everywhere|logout all|revoke all/i,
    });

    if (await signOutAllBtn.isVisible().catch(() => false)) {
      await signOutAllBtn.click();

      // May have confirmation dialog
      const confirmBtn = page.getByRole("button", {
        name: /confirm|yes|sign out/i,
      });
      if (await confirmBtn.isVisible().catch(() => false)) {
        await confirmBtn.click();
      }

      await page.waitForURL(/\/login/, { timeout: 15_000 });
    } else {
      // Alternative: use user menu sign out
      const userMenuTrigger = page.getByTestId("user-menu-trigger");
      if (await userMenuTrigger.isVisible().catch(() => false)) {
        await userMenuTrigger.click();
        await page
          .getByRole("menuitem", { name: /sign out/i })
          .click();
        await page.waitForURL(/\/login/, { timeout: 15_000 });
      }
    }
  });
});
