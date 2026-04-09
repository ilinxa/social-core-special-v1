/**
 * Network Page Object Models.
 *
 * User network route: /network
 * (Business network routes are in business-network.page.ts)
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

/** User's network overview page (/network). */
export class MyNetworkPage extends BasePage {
  readonly heading: Locator;

  // --- Stats ---
  readonly connectionsCount: Locator;
  readonly followingCount: Locator;

  // --- Tabs ---
  readonly connectionsTab: Locator;
  readonly followingTab: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- Empty states ---
  readonly noConnectionsMessage: Locator;
  readonly notFollowingMessage: Locator;
  readonly noSearchResultsMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /my network/i });

    // Stats text (e.g. "5 connections", "3 following")
    this.connectionsCount = page.getByText(/\d+ connections/);
    this.followingCount = page.getByText(/\d+ following/);

    // Tabs
    this.connectionsTab = page.getByRole('tab', { name: /connections/i });
    this.followingTab = page.getByRole('tab', { name: /following/i });

    // Search
    this.searchInput = page.getByPlaceholder(/search/i);

    // Empty states
    this.noConnectionsMessage = page.getByText(/no connections yet/i);
    this.notFollowingMessage = page.getByText(/not following anyone yet/i);
    this.noSearchResultsMessage = page.getByText(/no results/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/network');
  }

  /** Get a disconnect button (on connections tab). */
  getDisconnectButton(): Locator {
    return this.page.getByRole('button', { name: /^disconnect$/i });
  }

  /** Get an unfollow button (on following tab). */
  getUnfollowButton(): Locator {
    return this.page.getByRole('button', { name: /^unfollow$/i });
  }
}
