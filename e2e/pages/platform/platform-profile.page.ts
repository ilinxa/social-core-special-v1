/**
 * Platform Profile Page Object Models.
 *
 * Public route: /platform/profile
 * Console edit route: /pconsole/profile
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PlatformPublicProfilePage extends BasePage {
  // --- Identity ---
  readonly platformName: Locator;
  readonly logo: Locator;

  // --- Sections ---
  readonly aboutSection: Locator;
  readonly contactSection: Locator;
  readonly brandingSection: Locator;
  readonly socialLinksSection: Locator;

  // --- Error state ---
  readonly notAvailableMessage: Locator;

  constructor(page: Page) {
    super(page);

    // h2 for platform name in profile view; logo alt is profile.name
    this.platformName = page.getByRole('heading', { level: 2 }).first();
    this.logo = page.getByRole('img').first();

    this.aboutSection = page.getByRole('heading', { name: /^about$/i });
    this.contactSection = page.getByRole('heading', { name: /contact/i });
    this.brandingSection = page.getByRole('heading', { name: /branding/i });
    this.socialLinksSection = page.getByRole('heading', { name: /social links/i });

    this.notAvailableMessage = page.getByText(/not available/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/platform/profile');
  }
}

export class PlatformProfileEditPage extends BasePage {
  readonly heading: Locator;

  // --- Tabs ---
  readonly editTab: Locator;
  readonly previewTab: Locator;

  // --- Form fields ---
  readonly nameInput: Locator;
  readonly taglineInput: Locator;
  readonly descriptionInput: Locator;
  readonly contactEmailInput: Locator;
  readonly contactPhoneInput: Locator;
  readonly addressInput: Locator;

  // --- Actions ---
  readonly saveButton: Locator;

  // --- Error ---
  readonly formError: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /profile/i });

    this.editTab = page.getByRole('tab', { name: /edit/i });
    this.previewTab = page.getByRole('tab', { name: /preview/i });

    this.nameInput = page.getByLabel('Name');
    this.taglineInput = page.getByLabel('Tagline');
    this.descriptionInput = page.getByLabel('Description');
    this.contactEmailInput = page.getByLabel('Contact email');
    this.contactPhoneInput = page.getByLabel('Contact phone');
    this.addressInput = page.getByLabel('Address');

    this.saveButton = page.getByRole('button', { name: /save changes/i });
    this.formError = page.getByRole('alert').filter({ hasNot: page.locator('#__next-route-announcer__') });
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/profile');
  }
}
