/**
 * Activity Page Object Model.
 *
 * Route: /activity
 * Shows user's transactions grouped by category with filter tabs.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class ActivityPage extends BasePage {
  readonly heading: Locator;

  // --- Filter tabs ---
  readonly allTab: Locator;
  readonly sentTab: Locator;
  readonly receivedTab: Locator;

  // --- Status filter ---
  readonly statusFilter: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /activity/i });

    // Tabs
    this.allTab = page.getByRole('tab', { name: /all/i });
    this.sentTab = page.getByRole('tab', { name: /sent/i });
    this.receivedTab = page.getByRole('tab', { name: /received/i });

    // Status filter dropdown
    this.statusFilter = page.getByLabel(/status/i);

    // Empty state
    this.emptyMessage = page.getByText(/no transactions found/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/activity');
  }

  async filterByDirection(direction: 'all' | 'sent' | 'received'): Promise<void> {
    const tab = { all: this.allTab, sent: this.sentTab, received: this.receivedTab }[direction];
    await tab.click();
  }

  async filterByStatus(status: string): Promise<void> {
    await this.statusFilter.selectOption(status);
  }

  /** Get all transaction category sections (accordion items). */
  getCategories(): Locator {
    return this.page.getByRole('group');
  }

  /** Get a specific transaction item by text. */
  getTransaction(text: string | RegExp): Locator {
    return this.page.getByRole('button', { name: text });
  }
}
