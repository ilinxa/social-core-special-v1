/**
 * Base Page Object — shared elements across all pages.
 *
 * Provides access to navigation, header, toasts, account switcher,
 * and common page interactions.
 */

import type { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;

  // --- Header / Topbar ---
  readonly brandLink: Locator;

  // --- Sidebar (desktop) ---
  readonly sidebarNav: Locator;

  // --- Bottom navbar (mobile) ---
  readonly bottomNavbar: Locator;

  // --- Account switcher ---
  readonly accountSwitcher: Locator;

  // --- Main content ---
  readonly main: Locator;

  constructor(page: Page) {
    this.page = page;

    // Header — brand link is the first link with the app name
    this.brandLink = page.getByRole('link', { name: /socialmedia adv/i });

    // Sidebar — uses aria-label="Sidebar navigation" from SidebarNav component
    this.sidebarNav = page.getByLabel('Sidebar navigation');

    // Bottom navbar — uses aria-label="Mobile navigation"
    this.bottomNavbar = page.getByLabel('Mobile navigation');

    // Account switcher — combobox with aria-label
    this.accountSwitcher = page.getByRole('combobox', { name: /switch account context/i });

    // Main content area — semantic landmark role
    this.main = page.getByRole('main');
  }

  // --- Navigation ---

  async navigateTo(path: string): Promise<void> {
    await this.page.goto(path);
  }

  /** Click a sidebar nav link by label text. */
  async clickSidebarLink(label: string): Promise<void> {
    await this.sidebarNav.getByRole('link', { name: new RegExp(label, 'i') }).click();
  }

  /** Get the active sidebar item (has aria-current="page"). */
  getActiveSidebarItem(): Locator {
    return this.sidebarNav.getByRole('link', { current: 'page' });
  }

  // --- User menu ---

  async openUserMenu(): Promise<void> {
    await this.page.getByRole('button', { name: /user menu/i }).click();
  }

  async clickUserMenuItem(label: string): Promise<void> {
    await this.openUserMenu();
    await this.page.getByRole('menuitem', { name: new RegExp(label, 'i') }).click();
  }

  async logout(): Promise<void> {
    await this.clickUserMenuItem('Log out');
  }

  // --- Account switcher ---

  async openAccountSwitcher(): Promise<void> {
    await this.accountSwitcher.click();
  }

  async switchToPersonal(): Promise<void> {
    await this.openAccountSwitcher();
    await this.page.getByText('Personal').first().click();
  }

  async switchToBusiness(businessName: string): Promise<void> {
    await this.openAccountSwitcher();
    await this.page.getByText(businessName).click();
  }

  async switchToPlatform(): Promise<void> {
    await this.openAccountSwitcher();
    await this.page.getByText('Platform').click();
  }

  // --- Toast notifications ---

  /** Get a toast by its text content. */
  getToast(text: string | RegExp): Locator {
    return this.page.locator('[data-sonner-toast]').filter({ hasText: text });
  }

  /** Get all visible toasts. */
  getAllToasts(): Locator {
    return this.page.locator('[data-sonner-toast]');
  }

  // --- Alerts ---

  /** Get an alert element by text. */
  getAlert(text: string | RegExp): Locator {
    return this.page.getByRole('alert').filter({ hasText: text });
  }

  // --- Common waits ---

  /** Wait for the main content area to be visible. */
  async waitForMainContent(): Promise<void> {
    await this.main.waitFor({ state: 'visible' });
  }

  /** Wait for page navigation to complete. */
  async waitForUrl(urlPattern: string | RegExp): Promise<void> {
    await this.page.waitForURL(urlPattern);
  }

  // --- Heading ---

  /** Get the page heading (first h1). */
  getHeading(): Locator {
    return this.page.getByRole('heading', { level: 1 });
  }
}
