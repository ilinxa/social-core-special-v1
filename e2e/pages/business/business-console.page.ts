/**
 * Business Console Page Object Models.
 *
 * Dashboard route: /bconsole/[slug]/dashboard
 * Settings route: /bconsole/[slug]/settings
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessDashboardPage extends BasePage {
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /business dashboard/i });
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/dashboard`);
  }
}

export class BusinessSettingsPage extends BasePage {
  readonly heading: Locator;

  // --- General ---
  readonly generalCard: Locator;

  // --- Danger zone ---
  readonly transferOwnershipButton: Locator;
  readonly archiveButton: Locator;
  readonly deleteButton: Locator;
  readonly leaveButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /settings/i });

    // General
    this.generalCard = page.getByRole('heading', { name: /general/i });

    // Danger zone actions
    this.transferOwnershipButton = page.getByRole('button', { name: /transfer/i });
    this.archiveButton = page.getByRole('button', { name: /archive/i });
    this.deleteButton = page.getByRole('button', { name: /delete/i });
    this.leaveButton = page.getByRole('button', { name: /leave/i });
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/settings`);
  }
}

export class BusinessProfileEditPage extends BasePage {
  readonly heading: Locator;

  // --- Tabs ---
  readonly editTab: Locator;
  readonly previewTab: Locator;

  // --- Form fields ---
  readonly displayNameInput: Locator;
  readonly taglineInput: Locator;
  readonly descriptionInput: Locator;
  readonly contactEmailInput: Locator;
  readonly contactPhoneInput: Locator;

  // --- Actions ---
  readonly saveButton: Locator;

  // --- Error ---
  readonly formError: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /profile/i });

    // Tabs
    this.editTab = page.getByRole('tab', { name: /edit/i });
    this.previewTab = page.getByRole('tab', { name: /preview/i });

    // Form
    this.displayNameInput = page.getByLabel('Display name');
    this.taglineInput = page.getByLabel('Tagline');
    this.descriptionInput = page.getByLabel('Description');
    this.contactEmailInput = page.getByLabel('Contact email');
    this.contactPhoneInput = page.getByLabel('Contact phone');

    // Actions
    this.saveButton = page.getByRole('button', { name: /save changes/i });

    // Error — exclude Next.js route announcer
    this.formError = page.getByRole('alert').filter({ hasNot: page.locator('#__next-route-announcer__') });
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/profile`);
  }
}
