/**
 * Notification Page Object Models.
 *
 * Notifications route: /notifications
 * Preferences: embedded in /settings page
 * Bell: embedded in Topbar (all authenticated pages)
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

// ---------------------------------------------------------------------------
// Notification Center Page
// ---------------------------------------------------------------------------

export class NotificationsPage extends BasePage {
  readonly heading: Locator;

  // Empty / disabled states
  readonly emptyHeading: Locator;
  readonly emptyDescription: Locator;
  readonly disabledHeading: Locator;

  // List elements
  readonly loadMoreButton: Locator;

  // Scope tabs
  readonly allTab: Locator;
  readonly personalTab: Locator;
  readonly businessTab: Locator;
  readonly platformTab: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /^notifications$/i });

    // Empty state
    this.emptyHeading = page.getByRole('heading', { name: /no notifications yet/i });
    this.emptyDescription = page.getByText(
      /when you receive notifications, they will appear here/i,
    );

    // Disabled state
    this.disabledHeading = page.getByRole('heading', {
      name: /notifications unavailable/i,
    });

    // List controls
    this.loadMoreButton = page.getByRole('button', { name: /load more/i });

    // Scope tabs
    this.allTab = page.getByRole('tab', { name: /^all\b/i });
    this.personalTab = page.getByRole('tab', { name: /personal/i });
    this.businessTab = page.getByRole('tab', { name: /business/i });
    this.platformTab = page.getByRole('tab', { name: /platform/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/notifications');
  }
}

// ---------------------------------------------------------------------------
// Notification Preferences (embedded in Settings page)
// ---------------------------------------------------------------------------

export class NotificationPreferencesSection extends BasePage {
  readonly sectionHeading: Locator;
  readonly sectionDescription: Locator;

  // Category cards
  readonly authCategory: Locator;
  readonly securityCategory: Locator;
  readonly transactionsCategory: Locator;
  readonly marketingCategory: Locator;
  readonly socialCategory: Locator;

  constructor(page: Page) {
    super(page);
    this.sectionHeading = page.getByRole('heading', {
      name: /notification preferences/i,
    });
    this.sectionDescription = page.getByText(
      /choose how you want to be notified/i,
    );

    // Category card titles — these are CardTitle headings in preference sections
    this.authCategory = page.getByRole('heading', { name: /authentication/i });
    this.securityCategory = page.getByRole('heading', { name: /security/i });
    this.transactionsCategory = page.getByRole('heading', { name: /transactions/i });
    this.marketingCategory = page.getByRole('heading', { name: /marketing/i });
    this.socialCategory = page.getByRole('heading', { name: /social/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/settings');
  }

  /** Get the email toggle switch for a given preference display name. */
  getEmailSwitch(displayName: string): Locator {
    return this.page.getByLabel(`${displayName} email notifications`);
  }

  /** Get the push toggle switch for a given preference display name. */
  getPushSwitch(displayName: string): Locator {
    return this.page.getByLabel(`${displayName} push notifications`);
  }

  /** Get the sms toggle switch for a given preference display name. */
  getSmsSwitch(displayName: string): Locator {
    return this.page.getByLabel(`${displayName} sms notifications`);
  }

  /** Get the reset button for a given preference display name. */
  getResetButton(displayName: string): Locator {
    return this.page.getByLabel(`Reset ${displayName} to default`);
  }

  /** Get the lock icon indicating a non-configurable type. */
  getLockIcon(): Locator {
    return this.page.getByLabel('Cannot be disabled');
  }
}

// ---------------------------------------------------------------------------
// Notification Bell Component (in Topbar)
// ---------------------------------------------------------------------------

export class NotificationBellComponent {
  readonly page: Page;
  readonly bellButton: Locator;
  readonly badge: Locator;

  // Dropdown (desktop popover)
  readonly dropdownHeading: Locator;
  readonly viewAllLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.bellButton = page.getByRole('button', { name: 'Notifications', exact: true });
    // Badge is a child of the bell button; use text content to find count
    this.badge = this.bellButton.getByText(/\d+/);

    // Dropdown elements (visible only when popover is open)
    this.dropdownHeading = page.getByRole('heading', { level: 4, name: /notifications/i });
    this.viewAllLink = page.getByRole('link', { name: /view all notifications/i });
  }

  /** Click the bell to open the dropdown (desktop). */
  async openDropdown(): Promise<void> {
    await this.bellButton.click();
  }
}
