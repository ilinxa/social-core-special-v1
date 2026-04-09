/**
 * Login Page Object Model.
 *
 * Route: /login
 * Elements: email, password, submit, OAuth buttons, forgot password link, sign up link.
 */

import type { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;

  // --- Form fields ---
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;

  // --- Links ---
  readonly forgotPasswordLink: Locator;
  readonly signUpLink: Locator;

  // --- OAuth ---
  readonly googleButton: Locator;
  readonly appleButton: Locator;

  // --- Messages ---
  readonly formError: Locator;
  readonly verifiedMessage: Locator;

  // --- Card ---
  readonly cardTitle: Locator;

  constructor(page: Page) {
    this.page = page;

    // Form
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password', { exact: true });
    this.submitButton = page.getByRole('button', { name: /sign in/i });

    // Links
    this.forgotPasswordLink = page.getByRole('link', { name: /forgot password/i });
    this.signUpLink = page.getByRole('link', { name: /sign up/i });

    // OAuth
    this.googleButton = page.getByRole('button', { name: /google/i });
    this.appleButton = page.getByRole('button', { name: /apple/i });

    // Messages — exclude Next.js route announcer which also has role="alert"
    this.formError = page.locator('[role="alert"]:not(#__next-route-announcer__)');
    this.verifiedMessage = page.getByRole('status');

    // Card — shadcn CardTitle renders as <div>, not <h2>
    this.cardTitle = page.locator('[data-slot="card-title"]');
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  async login(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    // Wait for login API response before returning, so auth tokens are stored
    // before any subsequent page.goto() that would cause a page reload
    const responsePromise = this.page
      .waitForResponse(
        (resp) => resp.url().includes('/auth/login'),
        { timeout: 10000 },
      )
      .catch(() => null);
    await this.submitButton.click();
    const resp = await responsePromise;
    // If login succeeded, wait for redirect to complete (tokens stored + route change)
    if (resp && resp.ok()) {
      await this.page
        .waitForURL(/\/(home|dashboard|verify)/, { timeout: 10000 })
        .catch(() => {});
    }
  }

  async getFormErrorText(): Promise<string> {
    return (await this.formError.textContent()) ?? '';
  }

  /** Check if the "Email verified" success banner is visible. */
  async isVerifiedBannerVisible(): Promise<boolean> {
    return this.verifiedMessage.isVisible();
  }
}
