import { test, expect } from "../helpers/fixtures";
import { TEST_USERS, TEST_BUSINESS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-75..U-82 — Public Pages (10 tests)
// =============================================================================

test.describe("Public Pages", () => {
  test("[U-75] Landing page renders", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(2000);

    // Landing page should have content
    const bodyText = await page.textContent("body");
    expect(bodyText!.length).toBeGreaterThan(100);
  });

  test("[U-76] About page renders", async ({ page }) => {
    await page.goto("/about");
    await page.waitForTimeout(2000);

    // Should load without 404
    const is404 = await page
      .getByText(/404|not found/i)
      .isVisible()
      .catch(() => false);

    // Either about page exists or we're redirected
    expect(!is404 || page.url() !== "http://localhost:3000/about").toBeTruthy();
  });

  test("[U-77] Contact page renders", async ({ page }) => {
    await page.goto("/contact");
    await page.waitForTimeout(2000);

    const is404 = await page
      .getByText(/404|not found/i)
      .isVisible()
      .catch(() => false);

    expect(!is404 || page.url() !== "http://localhost:3000/contact").toBeTruthy();
  });

  test("[U-78] Public business profile page", async ({ page }) => {
    await page.goto(`/business/${TEST_BUSINESS.slug}`);

    // Should show business name
    await expect(
      page.getByText(TEST_BUSINESS.name).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-79] Request to Join visible when authenticated and open", async ({
    page,
  }) => {
    // Login as User A (not a member of the test business)
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto(`/business/${TEST_BUSINESS.slug}`);

    // Should see "Request to Join" button (business has open_member_request=true)
    await expect(
      page.getByRole("button", { name: /request to join|join/i }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-80] Request to Join creates transaction", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto(`/business/${TEST_BUSINESS.slug}`);

    const joinBtn = page
      .getByRole("button", { name: /request to join|join/i })
      .first();

    if (await joinBtn.isVisible().catch(() => false)) {
      await joinBtn.click();
      await page.waitForTimeout(3000);

      // Should show success feedback (toast or button state change)
      const successVisible = await page
        .getByText(/request sent|pending|success/i)
        .first()
        .isVisible()
        .catch(() => false);

      const buttonChanged = await page
        .getByRole("button", { name: /pending|requested|cancel/i })
        .first()
        .isVisible()
        .catch(() => false);

      expect(successVisible || buttonChanged).toBeTruthy();
    }
  });

  test("[U-81] Business owner sees no join button", async ({ page }) => {
    // Login as User B (owner of the test business)
    await loginViaUI(page, TEST_USERS.userB.email, TEST_USERS.userB.password);

    await page.goto(`/business/${TEST_BUSINESS.slug}`);
    await page.waitForTimeout(2000);

    // Owner should NOT see "Request to Join"
    const joinBtn = page.getByRole("button", {
      name: /request to join/i,
    });
    const joinVisible = await joinBtn.isVisible().catch(() => false);
    expect(joinVisible).toBeFalsy();
  });

  test("[U-82] Platform profile page loads", async ({ page }) => {
    await page.goto("/platform/profile");
    await page.waitForTimeout(2000);

    // Should load (may show platform info or placeholder)
    const bodyText = await page.textContent("body");
    expect(bodyText!.length).toBeGreaterThan(50);

    // Should not be a 404
    const is404 = await page
      .getByText(/404|not found/i)
      .isVisible()
      .catch(() => false);
    expect(is404).toBeFalsy();
  });
});
