/**
 * Navigation helper — common navigation operations for tests.
 *
 * Provides route navigation, URL assertions, and toast verification.
 */

import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

/**
 * Navigate to a route and wait for the page to load.
 */
export async function goTo(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.waitForLoadState('load');
}

/**
 * Assert the current URL matches a path or pattern.
 */
export async function expectRoute(page: Page, pathOrPattern: string | RegExp): Promise<void> {
  await expect(page).toHaveURL(pathOrPattern);
}

/**
 * Assert the page title contains the given text.
 */
export async function expectTitle(page: Page, title: string | RegExp): Promise<void> {
  await expect(page).toHaveTitle(title);
}

/**
 * Get a toast notification by text content.
 */
export function getToast(page: Page, text: string | RegExp): Locator {
  return page.locator('[data-sonner-toast]').filter({ hasText: text });
}

/**
 * Wait for a toast to appear and optionally verify its text.
 */
export async function waitForToast(page: Page, text: string | RegExp): Promise<void> {
  const toast = getToast(page, text);
  await toast.waitFor({ state: 'visible' });
}

/**
 * Assert an alert message is visible on the page.
 */
export async function expectAlert(page: Page, text: string | RegExp): Promise<void> {
  await expect(page.getByRole('alert').filter({ hasText: text })).toBeVisible();
}

/**
 * Switch account context via the account switcher.
 */
export async function switchAccountContext(
  page: Page,
  context: 'Personal' | string,
): Promise<void> {
  const switcher = page.getByRole('combobox', { name: /switch account context/i });
  await switcher.click();
  await page.getByText(context).first().click();
}

/**
 * Assert the sidebar has an active nav item with the given label.
 */
export async function expectActiveNavItem(page: Page, label: string): Promise<void> {
  const activeItem = page.getByLabel('Sidebar navigation').getByRole('link', { current: 'page' });
  await expect(activeItem).toContainText(label);
}

/**
 * Click a navigation link in the sidebar.
 */
export async function clickNavLink(page: Page, label: string): Promise<void> {
  const nav = page.getByLabel('Sidebar navigation');
  await nav.getByRole('link', { name: new RegExp(label, 'i') }).click();
}
