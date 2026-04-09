/**
 * Forgot Password Page Object Model.
 *
 * Route: /forgot-password
 * Elements: email input, submit, back to sign in link, success message.
 */

import type { Page, Locator } from '@playwright/test';

export class ForgotPasswordPage {
  readonly page: Page;

  // --- Form fields ---
  readonly emailInput: Locator;
  readonly submitButton: Locator;

  // --- Links ---
  readonly backToSignInLink: Locator;

  // --- Messages ---
  readonly formError: Locator;
  readonly successMessage: Locator;

  // --- Card ---
  readonly cardTitle: Locator;

  constructor(page: Page) {
    this.page = page;

    // Form
    this.emailInput = page.getByLabel('Email');
    this.submitButton = page.getByRole('button', { name: /send reset link/i });

    // Links
    this.backToSignInLink = page.getByRole('link', { name: /back to sign in/i });

    // Messages — exclude Next.js route announcer
    this.formError = page.locator('[role="alert"]:not(#__next-route-announcer__)');
    this.successMessage = page.getByText(/sent a password reset link/i);

    // Card — shadcn CardTitle renders as <div>
    this.cardTitle = page.locator('[data-slot="card-title"]');
  }

  async goto(): Promise<void> {
    await this.page.goto('/forgot-password');
  }

  async requestReset(email: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.submitButton.click();
  }
}
