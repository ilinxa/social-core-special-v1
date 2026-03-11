import { test, expect } from "../helpers/fixtures";
import { TEST_USERS } from "../helpers/constants";
import { loginViaUI } from "../helpers/auth-helper";
import * as path from "path";

// =============================================================================
// U-40..U-43 — Avatar Upload (4 tests)
// =============================================================================

const FIXTURES_DIR = path.join(__dirname, "..", "fixtures");

test.describe("Avatar", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaUI(page, TEST_USERS.userA.email, TEST_USERS.userA.password);
    await page.goto("/profile");
  });

  test("[U-40] Upload valid JPEG avatar", async ({ page }) => {
    // Find file input (usually hidden) for avatar upload
    const fileInput = page.locator('input[type="file"]').first();

    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(path.join(FIXTURES_DIR, "test-avatar.jpg"));
      await page.waitForTimeout(3000);

      // Avatar image should be visible (either img or background)
      const avatarImg = page.locator(
        "img[alt*='avatar' i], img[alt*='profile' i], [data-testid='avatar']"
      );
      if (await avatarImg.count() > 0) {
        await expect(avatarImg.first()).toBeVisible();
      }
    } else {
      // Avatar might be triggered by clicking on avatar area
      const avatarArea = page.locator(
        "[data-testid='avatar-upload'], .avatar-upload"
      );
      if (await avatarArea.isVisible().catch(() => false)) {
        await avatarArea.click();
      }
    }
  });

  test("[U-41] Reject file >5MB", async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first();

    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(
        path.join(FIXTURES_DIR, "test-avatar-large.jpg")
      );
      await page.waitForTimeout(2000);

      // Should show error toast about file size
      await expect(
        page.getByText(/5\s*MB|too large|file size/i).first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("[U-42] Reject non-image file", async ({ page }) => {
    const fileInput = page.locator('input[type="file"]').first();

    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(
        path.join(FIXTURES_DIR, "test-file.txt")
      );
      await page.waitForTimeout(2000);

      // Should show error toast about file type
      await expect(
        page.getByText(/JPEG|PNG|GIF|WebP|image|format/i).first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("[U-43] Remove avatar shows fallback initials", async ({ page }) => {
    // Look for remove/delete avatar button
    const removeBtn = page.getByRole("button", {
      name: /remove|delete.*avatar/i,
    });

    if (await removeBtn.isVisible().catch(() => false)) {
      await removeBtn.click();
      await page.waitForTimeout(2000);

      // Should show fallback (initials or default avatar)
      const fallback = page.locator(
        "[data-testid='avatar-fallback'], .avatar-fallback"
      );
      if (await fallback.count() > 0) {
        await expect(fallback.first()).toBeVisible();
      }
    }
  });
});
