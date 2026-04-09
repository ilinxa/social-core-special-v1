/**
 * Platform Console Page Object Models.
 *
 * Dashboard route: /pconsole/dashboard
 * Settings route: /pconsole/settings
 * Businesses route: /pconsole/businesses
 * Audit route: /pconsole/audit
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PlatformDashboardPage extends BasePage {
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /platform dashboard/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/dashboard');
  }
}

export class PlatformSettingsPage extends BasePage {
  readonly heading: Locator;

  // --- General ---
  readonly generalCard: Locator;

  // --- Danger zone ---
  readonly transferOwnershipButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /settings/i });
    this.generalCard = page.getByRole('heading', { name: /general/i });
    this.transferOwnershipButton = page.getByRole('button', { name: /transfer/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/settings');
  }
}

export class PlatformBusinessesPage extends BasePage {
  readonly heading: Locator;
  readonly placeholderText: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /businesses/i });
    this.placeholderText = page.getByText(/coming soon/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/businesses');
  }
}

export class PlatformAuditPage extends BasePage {
  readonly heading: Locator;
  readonly placeholderText: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /audit log/i });
    this.placeholderText = page.getByText(/coming soon/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/audit');
  }
}
