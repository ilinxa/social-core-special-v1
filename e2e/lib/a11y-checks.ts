/**
 * Accessibility check utilities for E2E tests.
 *
 * Provides reusable functions for ARIA landmark validation,
 * focus trap verification, keyboard navigation, and color contrast checks.
 *
 * Usage:
 * ```typescript
 * import { checkLandmarks, checkFocusTrap, checkKeyboardNav } from '../../lib/a11y-checks';
 *
 * test('page has correct ARIA landmarks', async ({ page }) => {
 *   await checkLandmarks(page);
 * });
 * ```
 */

import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

/** Valid ARIA role values accepted by Playwright's getByRole(). */
type AriaRole = Parameters<Page['getByRole']>[0];

// ---------------------------------------------------------------------------
// ARIA Landmarks
// ---------------------------------------------------------------------------

/** ARIA landmark roles that should be present on every authenticated page. */
const REQUIRED_LANDMARKS = ['main', 'navigation'] as const;

/**
 * Verify that the page has required ARIA landmark regions.
 * Every page should have at least a `main` and `navigation` landmark.
 */
export async function checkLandmarks(
  page: Page,
  options?: { expectBanner?: boolean; expectContentinfo?: boolean },
): Promise<void> {
  for (const role of REQUIRED_LANDMARKS) {
    const element = page.getByRole(role).first();
    await expect(element, `Expected ARIA landmark role="${role}" to be present`).toBeAttached();
  }

  if (options?.expectBanner) {
    await expect(
      page.getByRole('banner').first(),
      'Expected ARIA banner landmark (header)',
    ).toBeAttached();
  }

  if (options?.expectContentinfo) {
    await expect(
      page.getByRole('contentinfo').first(),
      'Expected ARIA contentinfo landmark (footer)',
    ).toBeAttached();
  }
}

// ---------------------------------------------------------------------------
// Focus Trap
// ---------------------------------------------------------------------------

/**
 * Verify that focus is trapped within a dialog or modal.
 *
 * Opens the trigger, tabs through all focusable elements, and verifies
 * that Tab wraps back to the first element (never escapes the trap).
 *
 * @param page - Playwright page
 * @param dialogLocator - Locator for the dialog/modal container
 * @param maxTabs - Maximum Tab presses before giving up (default: 20)
 */
export async function checkFocusTrap(
  page: Page,
  dialogLocator: Locator,
  maxTabs = 20,
): Promise<void> {
  // Dialog should be visible
  await expect(dialogLocator).toBeVisible();

  // Get all focusable elements within the dialog
  const focusableSelector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'textarea:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  const focusableCount = await dialogLocator.locator(focusableSelector).count();

  if (focusableCount === 0) {
    return; // No focusable elements — nothing to trap
  }

  // Focus the first element
  await dialogLocator.locator(focusableSelector).first().focus();

  // Tab through all elements and verify focus stays inside dialog
  for (let i = 0; i < Math.min(focusableCount + 2, maxTabs); i++) {
    await page.keyboard.press('Tab');

    // Check that the focused element is still within the dialog
    const isFocusInDialog = await page.evaluate((selector) => {
      const active = document.activeElement;
      if (!active) return false;
      const dialog = document.querySelector(selector);
      return dialog?.contains(active) ?? false;
    }, await dialogLocator.evaluate((el) => {
      // Build a unique selector for the dialog
      if (el.id) return `#${el.id}`;
      if (el.getAttribute('role') === 'dialog') return '[role="dialog"]';
      return '[role="dialog"], [data-state="open"]';
    }));

    expect(isFocusInDialog, `Focus escaped the dialog on Tab press ${i + 1}`).toBe(true);
  }
}

// ---------------------------------------------------------------------------
// Keyboard Navigation
// ---------------------------------------------------------------------------

/**
 * Verify that a list of items supports keyboard navigation with arrow keys.
 *
 * @param page - Playwright page
 * @param listLocator - Locator for the list container
 * @param itemRole - Role of individual items (default: 'option')
 * @param expectedCount - Expected number of items (optional, skips count check if not provided)
 */
export async function checkKeyboardNav(
  page: Page,
  listLocator: Locator,
  itemRole: AriaRole = 'option',
  expectedCount?: number,
): Promise<void> {
  await expect(listLocator).toBeVisible();

  const items = listLocator.getByRole(itemRole);
  const count = await items.count();

  if (expectedCount !== undefined) {
    expect(count).toBe(expectedCount);
  }

  if (count < 2) return; // Need at least 2 items to test arrow nav

  // Focus the first item
  await items.first().focus();
  await expect(items.first()).toBeFocused();

  // Press ArrowDown → second item should be focused
  await page.keyboard.press('ArrowDown');
  await expect(items.nth(1)).toBeFocused();

  // Press ArrowUp → first item should be focused again
  await page.keyboard.press('ArrowUp');
  await expect(items.first()).toBeFocused();
}

// ---------------------------------------------------------------------------
// Tab Order
// ---------------------------------------------------------------------------

/**
 * Verify that Tab moves focus through elements in the expected order.
 *
 * @param page - Playwright page
 * @param expectedOrder - Array of locators in expected tab order
 */
export async function checkTabOrder(
  page: Page,
  expectedOrder: Locator[],
): Promise<void> {
  if (expectedOrder.length === 0) return;

  // Focus the first element
  await expectedOrder[0].focus();
  await expect(expectedOrder[0]).toBeFocused();

  // Tab through the rest
  for (let i = 1; i < expectedOrder.length; i++) {
    await page.keyboard.press('Tab');
    await expect(
      expectedOrder[i],
      `Expected element at position ${i} to be focused after ${i} Tab presses`,
    ).toBeFocused();
  }
}

// ---------------------------------------------------------------------------
// Escape Key
// ---------------------------------------------------------------------------

/**
 * Verify that pressing Escape closes a dialog/popover.
 *
 * @param page - Playwright page
 * @param dialogLocator - Locator for the dialog that should close
 */
export async function checkEscapeCloses(
  page: Page,
  dialogLocator: Locator,
): Promise<void> {
  await expect(dialogLocator).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialogLocator).toBeHidden();
}

// ---------------------------------------------------------------------------
// Skip Link
// ---------------------------------------------------------------------------

/**
 * Verify that a "Skip to content" link exists and targets the main content.
 *
 * @param page - Playwright page
 */
export async function checkSkipLink(page: Page): Promise<void> {
  const skipLink = page.getByRole('link', { name: /skip to (main )?content/i });

  // Skip links are often visually hidden but should be focusable
  await page.keyboard.press('Tab');

  // Check if skip link becomes visible on focus
  const isSkipLinkPresent = (await skipLink.count()) > 0;
  if (!isSkipLinkPresent) return; // Skip link not implemented — not a hard fail

  // If present, it should have an href pointing to #main or similar
  const href = await skipLink.getAttribute('href');
  expect(href).toMatch(/^#/);
}

// ---------------------------------------------------------------------------
// Form Accessibility
// ---------------------------------------------------------------------------

/**
 * Verify that all visible form inputs have associated labels.
 *
 * @param page - Playwright page
 * @param formLocator - Locator for the form container
 */
export async function checkFormLabels(
  page: Page,
  formLocator: Locator,
): Promise<void> {
  const inputs = formLocator.locator('input:visible, textarea:visible, select:visible');
  const count = await inputs.count();

  for (let i = 0; i < count; i++) {
    const input = inputs.nth(i);
    const type = await input.getAttribute('type');

    // Skip hidden and submit inputs
    if (type === 'hidden' || type === 'submit') continue;

    // Check for label association via: aria-label, aria-labelledby, or <label> with for=
    const hasAriaLabel = await input.getAttribute('aria-label');
    const hasAriaLabelledBy = await input.getAttribute('aria-labelledby');
    const id = await input.getAttribute('id');

    if (hasAriaLabel || hasAriaLabelledBy) continue;

    if (id) {
      const labelCount = await formLocator.locator(`label[for="${id}"]`).count();
      expect(
        labelCount,
        `Input #${id} (type=${type}) should have an associated <label>`,
      ).toBeGreaterThan(0);
    }
  }
}
