/**
 * Settings Page Object Model.
 *
 * Route: /settings
 * Sections: username change, danger zone (deactivate).
 *
 * Security/Sessions Page Object Model.
 *
 * Route: /sessions
 * Sections: active sessions, change password.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class SettingsPage extends BasePage {
  readonly heading: Locator;

  // --- Username section ---
  readonly usernameInput: Locator;
  readonly updateUsernameButton: Locator;

  // --- Danger zone ---
  readonly deactivateButton: Locator;
  readonly deactivateConfirmInput: Locator;
  readonly deactivateConfirmButton: Locator;
  readonly deactivateCancelButton: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1 });

    // Username
    this.usernameInput = page.getByLabel(/username/i);
    this.updateUsernameButton = page.getByRole('button', { name: /update username/i });

    // Danger zone
    this.deactivateButton = page.getByRole('button', { name: 'Deactivate' });
    this.deactivateConfirmInput = page.getByPlaceholder("Type 'deactivate' to confirm");
    this.deactivateConfirmButton = page.getByRole('button', { name: /deactivate account/i });
    this.deactivateCancelButton = page.getByRole('button', { name: /cancel/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/settings');
  }

  async changeUsername(newUsername: string): Promise<void> {
    await this.usernameInput.fill(newUsername);
    await this.updateUsernameButton.click();
  }

  async initiateDeactivation(): Promise<void> {
    await this.deactivateButton.click();
  }

  async confirmDeactivation(): Promise<void> {
    await this.deactivateConfirmInput.fill('deactivate');
    await this.deactivateConfirmButton.click();
  }
}

export class SecurityPage extends BasePage {
  readonly heading: Locator;

  // --- Sessions ---
  readonly sessionsSection: Locator;

  // --- Change password ---
  readonly currentPasswordInput: Locator;
  readonly newPasswordInput: Locator;
  readonly changePasswordButton: Locator;

  constructor(page: Page) {
    super(page);

    this.heading = page.getByRole('heading', { level: 1, name: /security/i });

    // Sessions — "Active Sessions" is a CardTitle (<div>), not a heading
    this.sessionsSection = page.getByText(/active sessions/i).first();

    // Change password — PasswordInput renders type="password" (not textbox role)
    this.currentPasswordInput = page.getByLabel('Current Password');
    this.newPasswordInput = page.getByLabel('New Password');
    this.changePasswordButton = page.getByRole('button', { name: /change password/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/sessions');
  }

  async changePassword(current: string, newPass: string): Promise<void> {
    await this.currentPasswordInput.fill(current);
    await this.newPasswordInput.fill(newPass);
    await this.changePasswordButton.click();
  }
}
