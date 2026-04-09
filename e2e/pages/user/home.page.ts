/**
 * Home Page Object Model.
 *
 * Route: /home
 * The main dashboard shown after login.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class HomePage extends BasePage {
  readonly heading: Locator;
  readonly welcomeText: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /dashboard/i });
    this.welcomeText = page.getByText(/welcome back/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/home');
  }
}
