/**
 * Reset Password Page Object Model.
 *
 * Route: /reset-password?token=<token>
 * Elements: new password input, submit, invalid token message.
 */

import type { Page, Locator } from '@playwright/test';

export class ResetPasswordPage {
  readonly page: Page;

  // --- Form fields ---
  readonly newPasswordInput: Locator;
  readonly submitButton: Locator;

  // --- Messages ---
  readonly formError: Locator;
  readonly invalidTokenMessage: Locator;
  readonly passwordStrength: Locator;

  // --- Card ---
  readonly cardTitle: Locator;

  constructor(page: Page) {
    this.page = page;

    // Form
    this.newPasswordInput = page.getByLabel('New Password');
    this.submitButton = page.getByRole('button', { name: /reset password/i });

    // Messages — exclude Next.js route announcer
    this.formError = page.locator('[role="alert"]:not(#__next-route-announcer__)');
    this.invalidTokenMessage = page.getByText(/invalid reset link/i);
    this.passwordStrength = page.getByRole('progressbar');

    // Card — shadcn CardTitle renders as <div>
    this.cardTitle = page.locator('[data-slot="card-title"]');
  }

  async goto(token?: string): Promise<void> {
    const url = token ? `/reset-password?token=${token}` : '/reset-password';
    await this.page.goto(url);
  }

  async resetPassword(newPassword: string): Promise<void> {
    await this.newPasswordInput.fill(newPassword);
    await this.submitButton.click();
  }
}
