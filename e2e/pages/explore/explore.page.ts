/**
 * Explore Page Object Models.
 *
 * Explore route: /explore
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

/** Explore search page — search bar, tabs, filters, results. */
export class ExplorePage extends BasePage {
  readonly heading: Locator;
  readonly subheading: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- Tabs ---
  readonly allTab: Locator;
  readonly businessesTab: Locator;
  readonly usersTab: Locator;

  // --- Filters ---
  readonly filtersButton: Locator;

  // --- Business filters ---
  readonly industrySelect: Locator;
  readonly businessTypeSelect: Locator;
  readonly companySizeSelect: Locator;
  readonly verifiedSwitch: Locator;

  // --- Sort ---
  readonly sortBySelect: Locator;

  // --- Results ---
  readonly businessResultCount: Locator;
  readonly userResultCount: Locator;

  // --- Empty states ---
  readonly noBusinessesMessage: Locator;
  readonly noUsersMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /explore/i });
    this.subheading = page.getByText(/discover businesses/i);

    // Search — Input has aria-label="Search" and type="search" (searchbox role)
    this.searchInput = page.getByRole('searchbox', { name: /search/i });

    // Tabs
    this.allTab = page.getByRole('tab', { name: /^all$/i });
    this.businessesTab = page.getByRole('tab', { name: /businesses/i });
    this.usersTab = page.getByRole('tab', { name: /users/i });

    // Filters toggle
    this.filtersButton = page.getByRole('button', { name: /filters/i });

    // Business filter selects (visible after "Businesses" tab + filters open)
    this.industrySelect = page.getByLabel(/^industry$/i);
    this.businessTypeSelect = page.getByLabel(/business type/i);
    this.companySizeSelect = page.getByLabel(/company size/i);
    this.verifiedSwitch = page.getByLabel(/^verified$/i);

    // Sort
    this.sortBySelect = page.getByLabel(/sort by/i);

    // Result counts
    this.businessResultCount = page.getByText(/\d+ businesses? found/);
    this.userResultCount = page.getByText(/\d+ users? found/);

    // Empty states
    this.noBusinessesMessage = page.getByText(/no businesses match your search/i);
    this.noUsersMessage = page.getByText(/no users match your search/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/explore');
  }

  /** Get the "Businesses" section heading in the All tab. */
  getBusinessesSectionHeading(): Locator {
    return this.page.getByRole('heading', { name: /^businesses$/i });
  }

  /** Get a "See all" button. */
  getSeeAllButton(): Locator {
    return this.page.getByRole('button', { name: /see all/i });
  }
}
