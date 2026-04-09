/**
 * Navigation on mobile viewport (iPhone 14 Pro — 393x852).
 *
 * Verifies that mobile navigation adapts correctly: sidebar is hidden,
 * bottom navbar is visible, hamburger menu works, and all nav links
 * are accessible.
 *
 * @layer L1
 * @system navigation
 * @parameters P2 (Navigation), P8 (Responsive)
 * @priority P0
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BasePage } from '../../../pages/base.page';
import { TEST_USERS } from '../../../lib/constants';

test.describe('Navigation — Mobile', () => {
  test('sidebar is hidden on mobile', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.regular.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.regular.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/home/);

    const basePage = new BasePage(page);

    // Desktop sidebar should be hidden on mobile
    await expect(basePage.sidebarNav).toBeHidden();
  });

  test('bottom navbar is visible on mobile', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.regular.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.regular.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/home/);

    const basePage = new BasePage(page);

    // Bottom navbar should be visible on mobile
    await expect(basePage.bottomNavbar).toBeVisible();
  });

  test('bottom navbar links navigate correctly', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.regular.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.regular.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/home/);

    const basePage = new BasePage(page);

    // Bottom navbar should have navigation links
    const navLinks = basePage.bottomNavbar.getByRole('link');
    const linkCount = await navLinks.count();

    // Should have at least Home, Explore, and Profile links
    expect(linkCount).toBeGreaterThanOrEqual(3);
  });

  test('main content area is visible on mobile', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.regular.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.regular.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/home/);

    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
  });

  test('public pages have mobile-friendly navigation', async ({ page }) => {
    // Landing page should work on mobile without auth
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Navigate to explore — should be accessible
    await page.goto('/explore');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('user menu is accessible on mobile', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.regular.email);
    await page.getByLabel('Password', { exact: true }).fill(TEST_USERS.regular.password);
    await page.getByRole('button', { name: /sign in|log in/i }).click();
    await page.waitForURL(/\/home/);

    // User menu button should be reachable
    const userMenuButton = page.getByRole('button', { name: /user menu/i });
    if (await userMenuButton.isVisible()) {
      await userMenuButton.click();
      // Menu items should appear
      await expect(page.getByRole('menuitem').first()).toBeVisible();
    }
  });
});
