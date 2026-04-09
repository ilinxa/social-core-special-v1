/**
 * Business Transactions Page Object Models.
 *
 * Dashboard route: /bconsole/[slug]/transactions
 * Requests route: /bconsole/[slug]/transactions/requests
 * Invitations route: /bconsole/[slug]/transactions/invitations
 * Settings route: /bconsole/[slug]/transactions/settings
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessTransactionsDashboardPage extends BasePage {
  readonly heading: Locator;

  // --- Dashboard cards ---
  readonly requestsCard: Locator;
  readonly invitationsCard: Locator;
  readonly settingsCard: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /transactions/i });

    // Cards use CardTitle which renders as <div>, not heading
    this.requestsCard = page.locator('[data-slot="card-title"]').filter({ hasText: /requests/i });
    this.invitationsCard = page.locator('[data-slot="card-title"]').filter({ hasText: /invitations/i });
    this.settingsCard = page.locator('[data-slot="card-title"]').filter({ hasText: /settings/i });
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/transactions`);
  }
}

export class TransactionListPage extends BasePage {
  readonly heading: Locator;

  // --- Status filter ---
  readonly allButton: Locator;
  readonly pendingButton: Locator;
  readonly acceptedButton: Locator;

  // --- List ---
  readonly emptyMessage: Locator;

  // --- Pagination ---
  readonly previousButton: Locator;
  readonly nextButton: Locator;
  readonly totalCount: Locator;

  constructor(page: Page, headingText: RegExp = /requests|invitations|transactions/i) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: headingText });

    // Status filters
    this.allButton = page.getByRole('button', { name: /^all$/i });
    this.pendingButton = page.getByRole('button', { name: /^pending$/i });
    this.acceptedButton = page.getByRole('button', { name: /accepted/i });

    // List
    this.emptyMessage = page.getByText(/no transactions found/i);

    // Pagination
    this.previousButton = page.getByRole('button', { name: /previous/i });
    this.nextButton = page.getByRole('button', { name: /next/i });
    this.totalCount = page.getByText(/\d+ total/i);
  }
}

export class TransactionSettingsPage extends BasePage {
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /transaction settings/i });
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/transactions/settings`);
  }
}
