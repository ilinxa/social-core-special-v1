/**
 * Verify Email Page Object Model.
 *
 * Route: /verify-email?email=<email>
 * Elements: email (may be pre-filled/disabled), code input, submit, resend button.
 */

import type { Page, Locator } from '@playwright/test';

export class VerifyEmailPage {
  readonly page: Page;

  // --- Form fields ---
  readonly emailInput: Locator;
  readonly codeInput: Locator;
  readonly submitButton: Locator;

  // --- Actions ---
  readonly resendButton: Locator;

  // --- Messages ---
  readonly formError: Locator;

  // --- Card ---
  readonly cardTitle: Locator;

  constructor(page: Page) {
    this.page = page;

    // Form
    this.emailInput = page.getByLabel('Email');
    this.codeInput = page.getByLabel('Verification Code');
    this.submitButton = page.getByRole('button', { name: /verify email/i });

    // Actions
    this.resendButton = page.getByRole('button', { name: /resend code/i });

    // Messages — exclude Next.js route announcer
    this.formError = page.locator('[role="alert"]:not(#__next-route-announcer__)');

    // Card — shadcn CardTitle renders as <div>
    this.cardTitle = page.locator('[data-slot="card-title"]');
  }

  async goto(email?: string): Promise<void> {
    const url = email ? `/verify-email?email=${encodeURIComponent(email)}` : '/verify-email';
    await this.page.goto(url);
  }

  async verify(code: string, email?: string): Promise<void> {
    if (email) {
      await this.emailInput.fill(email);
    }
    await this.codeInput.fill(code);
    await this.submitButton.click();
  }

  async resendCode(): Promise<void> {
    await this.resendButton.click();
  }

  /** Check if resend button is in cooldown state (disabled with countdown). */
  async isResendOnCooldown(): Promise<boolean> {
    return this.resendButton.isDisabled();
  }
}
