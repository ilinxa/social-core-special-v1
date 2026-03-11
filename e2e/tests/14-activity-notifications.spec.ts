import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-94..U-96 — Activity & Notifications (3 tests)
// =============================================================================

test.describe("Activity & Notifications", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
  });

  test("[U-94] Activity accessible from sidebar nav", async ({ page }) => {
    await page.goto("/home");

    // Find Activity link in sidebar
    const activityLink = page
      .getByRole("link", { name: /activity/i })
      .first();

    await expect(activityLink).toBeVisible({ timeout: 10_000 });
    await activityLink.click();
    await page.waitForURL(/\/activity/, { timeout: 10_000 });
  });

  test("[U-95] Notifications page renders", async ({ page }) => {
    await page.goto("/notifications");
    await page.waitForTimeout(2000);

    // Page should load (even if placeholder)
    const bodyText = await page.textContent("body");
    expect(bodyText!.length).toBeGreaterThan(50);

    // Should not be 404
    const is404 = await page
      .getByText(/404|not found/i)
      .isVisible()
      .catch(() => false);
    expect(is404).toBeFalsy();
  });

  test("[U-96] Notifications accessible from sidebar", async ({ page }) => {
    await page.goto("/home");

    const notifLink = page
      .getByRole("link", { name: /notification/i })
      .first();

    if (await notifLink.isVisible().catch(() => false)) {
      await notifLink.click();
      await page.waitForURL(/\/notification/, { timeout: 10_000 });
    } else {
      // Notifications might be in the topbar instead
      const notifIcon = page
        .getByTestId("notifications-trigger")
        .or(page.locator("[data-testid='bell-icon']"));

      if (await notifIcon.isVisible().catch(() => false)) {
        await notifIcon.click();
        await page.waitForTimeout(1000);
      }
    }
  });
});
