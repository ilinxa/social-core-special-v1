/**
 * Platform Members Page Object Model.
 *
 * Route: /pconsole/members
 * Reuses member/role patterns from business (shared components).
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PlatformMembersPage extends BasePage {
  readonly heading: Locator;

  // --- Search ---
  readonly searchInput: Locator;

  // --- Tabs (status filter) ---
  readonly allTab: Locator;
  readonly activeTab: Locator;

  // --- Role list ---
  readonly rolesHeading: Locator;
  readonly createRoleButton: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  // --- Quota ---
  readonly quotaBar: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /platform members/i });

    this.searchInput = page.getByPlaceholder(/search members/i);

    this.allTab = page.getByRole('tab', { name: /all/i }).or(
      page.getByRole('button', { name: /^all$/i }),
    );
    this.activeTab = page.getByRole('tab', { name: /active/i }).or(
      page.getByRole('button', { name: /^active$/i }),
    );

    this.rolesHeading = page.getByRole('heading', { name: /roles/i });
    this.createRoleButton = page.getByRole('button', { name: /create role/i });
    this.emptyMessage = page.getByText(/no members found/i);
    // QuotaBar renders text like "2 / 10"
    this.quotaBar = page.getByRole('progressbar').or(page.getByText(/\d+\s*\/\s*\d+/));
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/members');
  }

  getMemberCard(name: string | RegExp): Locator {
    return this.page.getByRole('button', { name });
  }

  getRoleCard(name: string | RegExp): Locator {
    return this.page.getByText(name);
  }
}
