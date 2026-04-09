/**
 * Business Network Page Object Models.
 *
 * Followers route: /bconsole/[slug]/network/followers
 * Connections route: /bconsole/[slug]/network/connections
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessFollowersPage extends BasePage {
  readonly heading: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- List ---
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /followers/i });
    this.searchInput = page.getByPlaceholder(/search followers/i);
    this.emptyMessage = page.getByText(/no followers/i);
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/network/followers`);
  }

  /** Get a follower row's remove button. */
  getRemoveButton(name: string | RegExp): Locator {
    return this.page.getByRole('button', { name: /remove/i });
  }
}

export class BusinessConnectionsPage extends BasePage {
  readonly heading: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- List ---
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /connections/i });
    this.searchInput = page.getByPlaceholder(/search connections/i);
    this.emptyMessage = page.getByText(/no connections/i);
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/network/connections`);
  }

  /** Get a connection row's disconnect button. */
  getDisconnectButton(name: string | RegExp): Locator {
    return this.page.getByRole('button', { name: /disconnect/i });
  }
}
