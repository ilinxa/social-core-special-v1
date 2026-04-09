/**
 * User-Level Transaction Page Object Models.
 *
 * Activity route: /activity
 * Detail route: /activity/[id]
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

/** User activity page (/activity). */
export class ActivityPage extends BasePage {
  readonly heading: Locator;

  // --- Filters ---
  readonly allTab: Locator;
  readonly sentTab: Locator;
  readonly receivedTab: Locator;
  readonly statusDropdown: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /activity/i });

    // Role filter tabs
    this.allTab = page.getByRole('tab', { name: /^all\b/i });
    this.sentTab = page.getByRole('tab', { name: /sent/i });
    this.receivedTab = page.getByRole('tab', { name: /received/i });

    // Status filter
    this.statusDropdown = page.getByRole('combobox', { name: /status/i });

    // Empty state
    this.emptyMessage = page.getByText(/no transactions found/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/activity');
  }

  /** Get a category section heading. */
  getCategoryHeading(name: string | RegExp): Locator {
    return this.page.getByRole('heading', { name });
  }
}

/** Transaction detail page (/activity/[id]). */
export class TransactionDetailPage extends BasePage {
  readonly heading: Locator;
  readonly statusBadge: Locator;
  readonly backButton: Locator;

  // --- Action buttons ---
  readonly acceptButton: Locator;
  readonly approveButton: Locator;
  readonly denyButton: Locator;
  readonly cancelButton: Locator;
  readonly dismissButton: Locator;
  readonly resubmitButton: Locator;
  readonly requestChangesButton: Locator;

  // --- Parties ---
  readonly partiesHeading: Locator;

  // --- Timeline ---
  readonly timelineHeading: Locator;

  // --- Form ---
  readonly formRequirementNotice: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /transaction detail/i });
    this.statusBadge = page.getByText(
      /pending|accepted|denied|cancelled|info requested|pending review/i,
    ).first();
    this.backButton = page.getByRole('button', { name: /back/i });

    // Actions
    this.acceptButton = page.getByRole('button', { name: /^accept$/i });
    this.approveButton = page.getByRole('button', { name: /^approve$/i });
    this.denyButton = page.getByRole('button', { name: /^deny$/i });
    this.cancelButton = page.getByRole('button', { name: /^cancel$/i });
    this.dismissButton = page.getByRole('button', { name: /^dismiss$/i });
    this.resubmitButton = page.getByRole('button', { name: /resubmit/i });
    this.requestChangesButton = page.getByRole('button', { name: /request changes/i });

    // Parties
    this.partiesHeading = page.getByRole('heading', { name: /parties/i });

    // Timeline
    this.timelineHeading = page.getByRole('heading', { name: /^activity$/i });

    // Form notice
    this.formRequirementNotice = page.getByText(/requires you to fill out/i);
  }

  async goto(id: string): Promise<void> {
    await this.page.goto(`/activity/${id}`);
  }
}

/** Transaction settings page (/bconsole/[slug]/transactions/settings or /pconsole/transactions/settings). */
export class TransactionSettingsPage extends BasePage {
  readonly heading: Locator;
  readonly description: Locator;

  // --- Membership requests toggle ---
  readonly membershipRequestsToggle: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /transaction settings/i });
    this.description = page.getByText(/configure forms required/i);
    this.membershipRequestsToggle = page.getByRole('switch', { name: /accept membership requests/i });
    this.emptyMessage = page.getByText(/no configurable transaction types/i);
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/transactions/settings`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/transactions/settings');
  }
}
