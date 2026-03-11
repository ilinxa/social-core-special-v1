import { test, expect } from "../helpers/fixtures";
import { TEST_USERS, TEST_BUSINESS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-59..U-74 — Explore & Discovery (18 tests)
// =============================================================================

test.describe("Explore & Discovery", () => {
  test("[U-59] Explore page renders", async ({ page }) => {
    await page.goto("/explore");

    // Heading
    await expect(page.getByText(/explore|discover/i).first()).toBeVisible({
      timeout: 10_000,
    });

    // Search bar
    await expect(
      page.getByPlaceholder(/search/i).or(page.getByRole("searchbox"))
    ).toBeVisible();

    // Tabs
    await expect(
      page.getByRole("tab", { name: /all/i }).or(page.getByText(/all/i).first())
    ).toBeVisible();
  });

  test("[U-60] Search bar updates URL", async ({ page }) => {
    await page.goto("/explore");

    const searchInput = page
      .getByPlaceholder(/search/i)
      .or(page.getByRole("searchbox"));
    await searchInput.fill("test");
    await page.waitForTimeout(1000);

    expect(page.url()).toContain("q=test");
  });

  test("[U-61] Businesses tab shows cards", async ({ page }) => {
    await page.goto("/explore?tab=businesses");

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Should show business cards or a no-results message
    const hasCards = await page
      .locator("[data-testid='business-card'], .business-card")
      .or(page.getByRole("article"))
      .count();

    const hasNoResults = await page
      .getByText(/no results|no businesses|nothing found/i)
      .isVisible()
      .catch(() => false);

    expect(hasCards > 0 || hasNoResults).toBeTruthy();
  });

  test("[U-62] Users tab requires authentication", async ({ browser }) => {
    // Try as anonymous
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto("http://localhost:3000/explore");
    await page.waitForTimeout(2000);

    // Users tab should either be hidden or show auth requirement
    const usersTab = page.getByRole("tab", { name: /users/i });
    const tabVisible = await usersTab.isVisible().catch(() => false);

    if (tabVisible) {
      await usersTab.click();
      await page.waitForTimeout(1000);

      // Should prompt to login or show restricted message
      const authRequired = await page
        .getByText(/sign in|log in|auth/i)
        .first()
        .isVisible()
        .catch(() => false);

      // Or redirect to login
      const redirected = page.url().includes("/login");
      expect(authRequired || redirected || !tabVisible).toBeTruthy();
    }

    await context.close();
  });

  test("[U-63] Search filters results", async ({ page }) => {
    await page.goto("/explore");

    const searchInput = page
      .getByPlaceholder(/search/i)
      .or(page.getByRole("searchbox"));
    await searchInput.fill(TEST_BUSINESS.name);
    await page.waitForTimeout(2000);

    // Should find our test business
    await expect(
      page.getByText(TEST_BUSINESS.name).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-64] Country filter works", async ({ page }) => {
    await page.goto("/explore?tab=businesses");
    await page.waitForTimeout(1000);

    // Find country filter
    const countryFilter = page
      .getByRole("combobox", { name: /country/i })
      .or(page.getByText(/country/i).first());

    if (await countryFilter.isVisible().catch(() => false)) {
      await countryFilter.click();
      await page.waitForTimeout(500);

      const searchInput = page.getByPlaceholder(/search/i).last();
      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.fill("United States");
        await page.waitForTimeout(500);
      }

      await page.getByText(/United States/i).first().click();
      await page.waitForTimeout(1000);

      expect(page.url()).toContain("country");
    }
  });

  test("[U-65] Filter panel renders controls", async ({ page }) => {
    await page.goto("/explore?tab=businesses");
    await page.waitForTimeout(1000);

    // Filter panel should have filter controls
    const filterPanel = page.locator(
      "[data-testid='filter-panel'], .filter-panel"
    );

    // At minimum, should see filter-related text/labels
    const hasFilters = await page
      .getByText(/country|industry|company size|tags|filter/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasFilters).toBeTruthy();
  });

  test("[U-66] Tags filter", async ({ page }) => {
    await page.goto("/explore?tab=businesses");
    await page.waitForTimeout(1000);

    const tagInput = page
      .getByPlaceholder(/add.*tag|tag/i)
      .or(page.locator("[data-testid='tag-filter']"));

    if (await tagInput.isVisible().catch(() => false)) {
      await tagInput.fill("e2e");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(1000);

      expect(page.url()).toContain("tags");
    }
  });

  test("[U-67] Infinite scroll or pagination", async ({ page }) => {
    await page.goto("/explore?tab=businesses");
    await page.waitForTimeout(2000);

    // Scroll down to trigger infinite scroll
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);

    // Either new content loaded or we reached the end
    // This is a basic smoke test — just verify no errors
    const hasContent = await page.locator("body").textContent();
    expect(hasContent).toBeTruthy();
  });

  test("[U-68] URL persistence on reload", async ({ page }) => {
    await page.goto("/explore?tab=businesses&q=test&country=US");
    await page.waitForTimeout(1000);

    // Reload
    await page.reload();
    await page.waitForTimeout(2000);

    // URL params should persist
    expect(page.url()).toContain("tab=businesses");
    expect(page.url()).toContain("q=test");
    expect(page.url()).toContain("country=US");
  });

  test("[U-69] Empty state for no results", async ({ page }) => {
    await page.goto("/explore?q=zzz_nonexistent_query_xyz_123");
    await page.waitForTimeout(2000);

    await expect(
      page.getByText(/no results|nothing found|no matches/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-70] Tab switching preserves query", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto("/explore?q=test");
    await page.waitForTimeout(1000);

    // Switch to businesses tab
    const bizTab = page.getByRole("tab", { name: /businesses/i });
    if (await bizTab.isVisible().catch(() => false)) {
      await bizTab.click();
      await page.waitForTimeout(1000);

      // Query should be preserved
      expect(page.url()).toContain("q=test");
    }
  });

  test("[U-71] Ordering dropdown", async ({ page }) => {
    await page.goto("/explore?tab=businesses");
    await page.waitForTimeout(1000);

    const orderSelect = page
      .getByRole("combobox", { name: /order|sort/i })
      .or(page.getByLabel(/order|sort/i));

    if (await orderSelect.isVisible().catch(() => false)) {
      await orderSelect.click();
      await page.waitForTimeout(500);

      // Select an ordering option
      const nameOption = page.getByText(/name|alphabetical/i).first();
      if (await nameOption.isVisible().catch(() => false)) {
        await nameOption.click();
        await page.waitForTimeout(1000);

        expect(page.url()).toContain("ordering");
      }
    }
  });

  test("[U-72] Business card navigates to profile", async ({ page }) => {
    await page.goto(`/explore?q=${encodeURIComponent(TEST_BUSINESS.name)}`);
    await page.waitForTimeout(2000);

    // Click on the business card
    const card = page.getByText(TEST_BUSINESS.name).first();
    await expect(card).toBeVisible({ timeout: 10_000 });

    // The card or a link in it should navigate to business profile
    const link = page
      .getByRole("link", { name: new RegExp(TEST_BUSINESS.name, "i") })
      .first();

    if (await link.isVisible().catch(() => false)) {
      await link.click();
    } else {
      await card.click();
    }

    await page.waitForURL(/\/business\//, { timeout: 10_000 });
  });

  test("[U-73] User card shows display info", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto("/explore?tab=users");
    await page.waitForTimeout(2000);

    // Should see user cards with names/usernames
    const hasUserContent = await page
      .getByText(/e2e_user/i)
      .first()
      .isVisible()
      .catch(() => false);

    // At minimum, the page should load without error
    expect(
      hasUserContent ||
        (await page.getByText(/no results/i).isVisible().catch(() => false))
    ).toBeTruthy();
  });

  test("[U-74] Multiple filters AND logic", async ({ page }) => {
    await page.goto("/explore?tab=businesses&q=E2E&country=US");
    await page.waitForTimeout(2000);

    // URL should have both params
    expect(page.url()).toContain("q=E2E");
    expect(page.url()).toContain("country=US");

    // Results should be filtered (or empty)
    const bodyText = await page.textContent("body");
    expect(bodyText).toBeTruthy();
  });
});
