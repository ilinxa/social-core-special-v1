/**
 * Profile Page Object Model — view and edit.
 *
 * View route: /profile
 * Edit route: /profile/edit
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class ProfileViewPage extends BasePage {
  readonly heading: Locator;
  readonly editButton: Locator;

  // --- Identity ---
  readonly displayName: Locator;
  readonly username: Locator;
  readonly email: Locator;
  readonly coverImage: Locator;
  readonly avatar: Locator;

  // --- Badges ---
  readonly verifiedBadge: Locator;

  // --- Sections ---
  readonly aboutSection: Locator;
  readonly personalInfoSection: Locator;
  readonly tagsSection: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /profile/i });
    // Edit Profile is a <button> (uses router.push), not a <link>
    this.editButton = page.getByRole('button', { name: /edit profile/i });

    // Identity
    this.displayName = page.getByRole('heading', { level: 2 }).first();
    this.username = page.getByText(/^@/);
    this.email = page.getByText(/@[\w.-]+\.[\w]+/);
    this.coverImage = page.getByAltText('Cover');
    // Avatar: when no image URL, renders <AvatarFallback> (initials), not <img>
    this.avatar = page.locator('[data-slot="avatar"]').first();

    // Badges
    this.verifiedBadge = page.getByText('Verified');

    // Sections (by heading text — locator targets the heading, tests scope from here)
    this.aboutSection = page.getByRole('heading', { name: /^about$/i });
    this.personalInfoSection = page.getByRole('heading', { name: /personal information/i });
    this.tagsSection = page.getByRole('heading', { name: /^tags$/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/profile');
  }

  async clickEdit(): Promise<void> {
    await this.editButton.click();
  }
}

export class ProfileEditPage extends BasePage {
  readonly heading: Locator;
  readonly backButton: Locator;

  // --- Form fields ---
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly phoneInput: Locator;
  readonly bioInput: Locator;
  readonly countrySelect: Locator;
  readonly citySelect: Locator;
  readonly timezoneSelect: Locator;
  readonly languageSelect: Locator;
  readonly publicProfileToggle: Locator;

  // --- Actions ---
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  // --- Messages ---
  readonly formError: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /edit profile/i });
    this.backButton = page.getByRole('button', { name: /back/i });

    // Form fields
    this.firstNameInput = page.getByLabel('First name');
    this.lastNameInput = page.getByLabel('Last name');
    this.phoneInput = page.getByLabel('Phone');
    this.bioInput = page.getByLabel('Bio');
    this.countrySelect = page.getByLabel('Country');
    this.citySelect = page.getByLabel('City');
    this.timezoneSelect = page.getByLabel('Timezone');
    this.languageSelect = page.getByLabel('Language');
    this.publicProfileToggle = page.getByLabel(/public profile/i);

    // Actions
    this.saveButton = page.getByRole('button', { name: /save changes/i });
    this.cancelButton = page.getByRole('link', { name: /cancel/i });

    // Messages — exclude Next.js route announcer
    this.formError = page.getByRole('alert').filter({ hasNot: page.locator('#__next-route-announcer__') });
  }

  async goto(): Promise<void> {
    await this.page.goto('/profile/edit');
  }

  async fillProfile(data: {
    firstName?: string;
    lastName?: string;
    phone?: string;
    bio?: string;
  }): Promise<void> {
    if (data.firstName !== undefined) await this.firstNameInput.fill(data.firstName);
    if (data.lastName !== undefined) await this.lastNameInput.fill(data.lastName);
    if (data.phone !== undefined) await this.phoneInput.fill(data.phone);
    if (data.bio !== undefined) await this.bioInput.fill(data.bio);
  }

  async save(): Promise<void> {
    await this.saveButton.click();
  }

  async cancel(): Promise<void> {
    await this.cancelButton.click();
  }
}
