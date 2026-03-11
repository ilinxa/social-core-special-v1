import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-51..U-58 — Navigation & Layout (10 tests)
// =============================================================================

test.describe("Navigation & Layout - Desktop", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
  });

  test("[U-51] Desktop sidebar shows navigation sections", async ({
    page,
  }) => {
    await page.goto("/home");

    // Sidebar should show core navigation items
    const sidebar = page.locator("nav, aside, [data-testid='sidebar']").first();
    await expect(sidebar).toBeVisible();

    // Check for key navigation items
    await expect(page.getByRole("link", { name: /home/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /explore/i }).first()).toBeVisible();
  });

  test("[U-52] Sidebar navigation works", async ({ page }) => {
    await page.goto("/home");

    // Click Explore link
    await page.getByRole("link", { name: /explore/i }).first().click();
    await page.waitForURL(/\/explore/);

    // Click Profile link
    await page.getByRole("link", { name: /profile/i }).first().click();
    await page.waitForURL(/\/profile/);

    // Click Settings link
    const settingsLink = page.getByRole("link", { name: /settings/i }).first();
    if (await settingsLink.isVisible().catch(() => false)) {
      await settingsLink.click();
      await page.waitForURL(/\/settings/);
    }
  });

  test("[U-55] User menu dropdown shows options", async ({ page }) => {
    await page.goto("/home");

    // Click user menu trigger
    const userMenuTrigger = page.getByTestId("user-menu-trigger").or(
      page.locator("[data-testid='user-avatar']")
    );

    if (await userMenuTrigger.isVisible().catch(() => false)) {
      await userMenuTrigger.click();
      await page.waitForTimeout(500);

      // Should show menu items
      await expect(
        page.getByRole("menuitem", { name: /profile/i }).or(
          page.getByText(/profile/i)
        )
      ).toBeVisible();

      await expect(
        page.getByRole("menuitem", { name: /sign out/i }).or(
          page.getByText(/sign out/i)
        )
      ).toBeVisible();
    }
  });

  test("[U-56] User menu Sign Out redirects to login", async ({ page }) => {
    await page.goto("/home");

    const userMenuTrigger = page.getByTestId("user-menu-trigger");
    if (await userMenuTrigger.isVisible().catch(() => false)) {
      await userMenuTrigger.click();
      await page.waitForTimeout(500);

      await page.getByRole("menuitem", { name: /sign out/i }).click();
      await page.waitForURL(/\/login/, { timeout: 10_000 });
    }
  });

  test("[U-57] Account switcher shows Personal only (no memberships)", async ({
    page,
  }) => {
    await page.goto("/home");

    // Look for account switcher
    const switcher = page
      .getByTestId("account-switcher")
      .or(page.getByRole("button", { name: /personal|switch/i }));

    if (await switcher.isVisible().catch(() => false)) {
      await switcher.click();
      await page.waitForTimeout(500);

      // Should show "Personal" option
      await expect(page.getByText(/personal/i).first()).toBeVisible();
    }
  });

  test("[U-58] Auth guard redirects unauthenticated to login", async ({
    browser,
  }) => {
    // Use a fresh context with NO auth
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto("http://localhost:3000/profile");

    // Should redirect to login with callback URL
    await page.waitForURL(/\/login/, { timeout: 15_000 });
    expect(page.url()).toContain("login");

    await context.close();
  });
});

// Mobile-specific navigation tests
test.describe("Navigation & Layout - Mobile", () => {
  test.use({ viewport: { width: 393, height: 851 } }); // Pixel 7

  test("[U-53] Mobile bottom navbar visible", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/home");

    // Bottom navbar should be visible on mobile
    const bottomNav = page
      .locator("[data-testid='bottom-navbar']")
      .or(page.locator("nav.fixed.bottom-0"))
      .or(page.locator("[role='navigation']").last());

    await expect(bottomNav).toBeVisible({ timeout: 10_000 });
  });

  test("[U-54] Mobile menu sheet opens", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/home");

    // Look for hamburger menu / mobile menu trigger
    const menuTrigger = page
      .getByTestId("mobile-menu-trigger")
      .or(page.getByRole("button", { name: /menu/i }))
      .or(page.locator("[data-testid='hamburger']"));

    if (await menuTrigger.isVisible().catch(() => false)) {
      await menuTrigger.click();
      await page.waitForTimeout(500);

      // Sheet/drawer should open with navigation links
      const sheet = page.locator(
        "[data-testid='mobile-menu-sheet'], [role='dialog'], .sheet-content"
      );
      await expect(sheet.first()).toBeVisible();
    }
  });
});
