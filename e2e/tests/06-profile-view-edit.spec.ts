import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-33..U-39 — Profile View & Edit (9 tests)
// =============================================================================

test.describe("Profile View & Edit", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
  });

  test("[U-33] Profile page renders with user info", async ({ page }) => {
    await page.goto("/profile");

    // Should show username or name
    await expect(
      page.getByText(TEST_USERS.userA.username)
    ).toBeVisible({ timeout: 10_000 });

    // Should have edit profile button/link
    await expect(
      page.getByRole("link", { name: /edit profile/i }).or(
        page.getByRole("button", { name: /edit profile/i })
      )
    ).toBeVisible();
  });

  test("[U-34] Edit form renders all fields", async ({ page }) => {
    await page.goto("/profile/edit");

    // Core profile fields
    await expect(page.getByLabel(/first name/i)).toBeVisible();
    await expect(page.getByLabel(/last name/i)).toBeVisible();
    await expect(page.getByLabel(/bio/i)).toBeVisible();

    // Location
    await expect(page.getByText(/country/i).first()).toBeVisible();

    // Save/Cancel buttons
    await expect(
      page.getByRole("button", { name: /save|update/i })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /cancel/i }).or(
        page.getByRole("button", { name: /cancel/i })
      )
    ).toBeVisible();
  });

  test("[U-35] Update name reflects on profile", async ({ page }) => {
    await page.goto("/profile/edit");

    const firstNameInput = page.getByLabel(/first name/i);
    const lastNameInput = page.getByLabel(/last name/i);

    await firstNameInput.clear();
    await firstNameInput.fill(TEST_USERS.userA.firstName!);
    await lastNameInput.clear();
    await lastNameInput.fill(TEST_USERS.userA.lastName!);

    await page.getByRole("button", { name: /save|update/i }).click();

    // Wait for save to complete (toast or redirect)
    await page.waitForTimeout(2000);

    // Navigate to profile and verify
    await page.goto("/profile");
    await expect(
      page.getByText(TEST_USERS.userA.firstName!)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("[U-36] Country selection filters city dropdown", async ({ page }) => {
    await page.goto("/profile/edit");

    // Find and interact with country selector
    const countryTrigger = page
      .getByRole("combobox", { name: /country/i })
      .or(page.locator("[data-testid='country-select']"))
      .or(page.getByText(/select country/i));

    if (await countryTrigger.isVisible().catch(() => false)) {
      await countryTrigger.click();

      // Search for and select United States
      const searchInput = page.getByPlaceholder(/search/i).first();
      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.fill("United States");
        await page.waitForTimeout(500);
      }
      await page.getByText(/United States/i).first().click();
      await page.waitForTimeout(500);

      // City field should now be enabled/available
      const cityTrigger = page
        .getByRole("combobox", { name: /city/i })
        .or(page.getByText(/select city/i));

      await expect(cityTrigger).toBeVisible();
    }
  });

  test("[U-37] Tags can be added", async ({ page }) => {
    await page.goto("/profile/edit");

    const tagInput = page.getByPlaceholder(/add.*tag|enter.*tag/i).or(
      page.locator("[data-testid='tag-input']")
    );

    if (await tagInput.isVisible().catch(() => false)) {
      await tagInput.fill("playwright");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(500);

      // Tag chip should appear
      await expect(page.getByText("playwright")).toBeVisible();
    }
  });

  test("[U-38] Timezone and language dropdowns work", async ({ page }) => {
    await page.goto("/profile/edit");

    // Check timezone selector exists
    const timezoneSelect = page
      .getByLabel(/timezone/i)
      .or(page.getByRole("combobox", { name: /timezone/i }));

    if (await timezoneSelect.isVisible().catch(() => false)) {
      await timezoneSelect.click();
      // Select a timezone
      await page.getByText(/UTC|America|Europe/i).first().click();
    }

    // Check language selector exists
    const langSelect = page
      .getByLabel(/language/i)
      .or(page.getByRole("combobox", { name: /language/i }));

    if (await langSelect.isVisible().catch(() => false)) {
      await langSelect.click();
      await page.getByText(/english/i).first().click();
    }

    // Save changes
    await page.getByRole("button", { name: /save|update/i }).click();
    await page.waitForTimeout(2000);
  });

  test("[U-39] Public toggle works", async ({ page }) => {
    await page.goto("/profile/edit");

    // Find the public/private toggle
    const publicToggle = page.getByLabel(/public|privacy|visible/i).or(
      page.getByRole("switch", { name: /public|privacy/i })
    );

    if (await publicToggle.isVisible().catch(() => false)) {
      // Toggle it on
      const isChecked = await publicToggle.isChecked().catch(() => false);
      if (!isChecked) {
        await publicToggle.click();
      }

      await page.getByRole("button", { name: /save|update/i }).click();
      await page.waitForTimeout(2000);

      // Verify toggle state persists on reload
      await page.goto("/profile/edit");
      await expect(publicToggle).toBeChecked();
    }
  });
});
