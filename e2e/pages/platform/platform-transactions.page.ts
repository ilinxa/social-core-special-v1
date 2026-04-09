/**
 * Platform Transactions Page Object Model.
 *
 * Route: /pconsole/transactions
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PlatformTransactionsDashboardPage extends BasePage {
  readonly heading: Locator;

  // --- Dashboard cards ---
  readonly requestsCard: Locator;
  readonly invitationsCard: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /transactions/i });
    // CardTitle renders as <div>, not heading
    this.requestsCard = page.locator('[data-slot="card-title"]').filter({ hasText: /requests/i });
    this.invitationsCard = page.locator('[data-slot="card-title"]').filter({ hasText: /invitations/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/transactions');
  }
}
