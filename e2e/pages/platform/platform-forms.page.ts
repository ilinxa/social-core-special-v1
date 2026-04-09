/**
 * Platform Forms Page Object Model.
 *
 * Route: /pconsole/forms
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PlatformFormsPage extends BasePage {
  readonly heading: Locator;

  // --- Dashboard cards ---
  readonly templatesHeading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /forms/i });
    // CardTitle renders as <div>, not heading
    this.templatesHeading = page.locator('[data-slot="card-title"]').filter({ hasText: /templates/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/pconsole/forms');
  }
}
