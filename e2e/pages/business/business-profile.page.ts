/**
 * Business Public Profile Page Object Model.
 *
 * Route: /business/[slug]
 * Renders the public-facing business profile (discovery page).
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessProfilePage extends BasePage {
  // --- Identity ---
  readonly businessName: Locator;
  readonly avatar: Locator;
  readonly coverImage: Locator;
  readonly verifiedBadge: Locator;

  // --- Actions ---
  readonly followButton: Locator;
  readonly requestToJoinButton: Locator;

  // --- Sections ---
  readonly aboutSection: Locator;
  readonly contactSection: Locator;
  readonly tagsSection: Locator;

  // --- States ---
  readonly privateNotice: Locator;
  readonly notFoundMessage: Locator;

  constructor(page: Page) {
    super(page);

    // Identity (h2 for business name in profile view)
    this.businessName = page.getByRole('heading', { level: 2 }).first();
    // Avatar alt text is the display_name; cover alt is "{display_name} cover"
    this.avatar = page.getByRole('img').first();
    this.coverImage = page.getByRole('img', { name: /cover$/i });
    this.verifiedBadge = page.getByText('Verified');

    // Actions
    this.followButton = page.getByRole('button', { name: /follow/i });
    this.requestToJoinButton = page.getByRole('button', { name: /request to join|join/i });

    // Sections
    this.aboutSection = page.getByRole('heading', { name: /^about$/i });
    this.contactSection = page.getByRole('heading', { name: /contact/i });
    this.tagsSection = page.getByRole('heading', { name: /^tags$/i });

    // States
    this.privateNotice = page.getByText(/private profile/i);
    this.notFoundMessage = page.getByText(/business not found/i);
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/business/${slug}`);
  }
}
