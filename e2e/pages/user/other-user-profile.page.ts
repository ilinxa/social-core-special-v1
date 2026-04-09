/**
 * Other User's Public Profile Page Object Model.
 *
 * Route: /users/[username]
 * Renders either full public profile or private profile notice.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class OtherUserProfilePage extends BasePage {
  readonly heading: Locator;

  // --- Identity ---
  readonly displayName: Locator;
  readonly username: Locator;
  readonly coverImage: Locator;
  readonly avatar: Locator;
  readonly verifiedBadge: Locator;

  // --- Actions ---
  readonly connectButton: Locator;

  // --- Sections ---
  readonly aboutSection: Locator;
  readonly infoSection: Locator;
  readonly tagsSection: Locator;

  // --- Private profile ---
  readonly privateNotice: Locator;

  // --- Not found ---
  readonly notFoundMessage: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /profile/i });

    // Identity
    this.displayName = page.getByRole('heading', { level: 2 }).first();
    this.username = page.getByText(/^@/);
    this.coverImage = page.getByAltText('Cover');
    this.avatar = page.getByRole('img', { name: /avatar/i });
    this.verifiedBadge = page.getByText('Verified');

    // Actions
    this.connectButton = page.getByRole('button', { name: /connect/i });

    // Sections (by heading text — locator targets the heading, tests scope from here)
    this.aboutSection = page.getByRole('heading', { name: /^about$/i });
    this.infoSection = page.getByRole('heading', { name: /personal information/i });
    this.tagsSection = page.getByRole('heading', { name: /^tags$/i });

    // Private
    this.privateNotice = page.getByText(/this profile is private/i);

    // Not found
    this.notFoundMessage = page.getByText(/user not found/i);
  }

  async goto(username: string): Promise<void> {
    await this.page.goto(`/users/${username}`);
  }
}
