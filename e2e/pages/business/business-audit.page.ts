/**
 * Business Audit Log Page Object Model.
 *
 * Route: /bconsole/[slug]/audit
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class BusinessAuditPage extends BasePage {
  readonly heading: Locator;

  // --- Coming soon placeholder ---
  readonly placeholderText: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /audit log/i });
    this.placeholderText = page.getByText(/coming soon|no audit/i);
  }

  async goto(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/audit`);
  }
}
