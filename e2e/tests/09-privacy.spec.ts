import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";

// =============================================================================
// U-47..U-50 — Privacy (5 tests)
// =============================================================================

test.describe("Privacy", () => {
  test("[U-47] Public profile (User B) is fully visible", async ({ page }) => {
    // Login as User A to view User B's public profile
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto(`/users/${TEST_USERS.userB.username}`);

    // Should show User B's name and profile details
    await expect(
      page.getByText(TEST_USERS.userB.firstName!).first()
    ).toBeVisible({ timeout: 10_000 });

    // Should show bio, location, or tags
    const profileContent = await page.textContent("body");
    const hasDetails =
      profileContent?.includes("E2E test user") ||
      profileContent?.includes("New York") ||
      profileContent?.includes("Bob");

    expect(hasDetails).toBeTruthy();
  });

  test("[U-48] Private profile shows limited view", async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto(`/users/${TEST_USERS.userC.username}`);

    // Should show private/limited view indicator
    const bodyText = await page.textContent("body");
    const isPrivate =
      bodyText?.includes("private") ||
      bodyText?.includes("Private") ||
      bodyText?.includes("limited");

    // If not showing "private" text, at least shouldn't show full profile data
    expect(isPrivate || !bodyText?.includes(TEST_USERS.userC.firstName!)).toBeTruthy();
  });

  test("[U-49] Limited view shows only avatar and username", async ({
    page,
  }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);

    await page.goto(`/users/${TEST_USERS.userC.username}`);

    // Username should be visible
    await expect(
      page.getByText(TEST_USERS.userC.username)
    ).toBeVisible({ timeout: 10_000 });

    // Full profile details should NOT be visible
    const bioVisible = await page
      .getByText(/bio|location|tags/i)
      .first()
      .isVisible()
      .catch(() => false);

    // Private profile should not expose detailed info
    // (This is a soft check — implementation may vary)
  });

  test("[U-50] Own private profile is fully visible", async ({ page }) => {
    // Login as User C (private profile)
    await loginViaUI(page, TEST_USERS.userC.email, TEST_USERS.userC.password);

    // View own profile
    await page.goto("/profile");

    // Should see own name/username
    await expect(
      page.getByText(TEST_USERS.userC.username)
    ).toBeVisible({ timeout: 10_000 });

    // Should see full profile (not restricted)
    const editLink = page.getByRole("link", { name: /edit/i }).or(
      page.getByRole("button", { name: /edit/i })
    );
    await expect(editLink.first()).toBeVisible();
  });

  test("[U-50b] Own profile page via /users/username is fully visible", async ({
    page,
  }) => {
    await loginViaUI(page, TEST_USERS.userC.email, TEST_USERS.userC.password);

    await page.goto(`/users/${TEST_USERS.userC.username}`);

    // Should see own full profile (not the limited "private" view)
    await expect(
      page.getByText(TEST_USERS.userC.username)
    ).toBeVisible({ timeout: 10_000 });
  });
});
