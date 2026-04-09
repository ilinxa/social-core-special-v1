/**
 * Register Page Object Model.
 *
 * Route: /register
 * Elements: email, username, password, confirm password, submit, OAuth, sign in link.
 */

import type { Page, Locator } from '@playwright/test';

export class RegisterPage {
  readonly page: Page;

  // --- Form fields ---
  readonly emailInput: Locator;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly submitButton: Locator;

  // --- Links ---
  readonly signInLink: Locator;

  // --- OAuth ---
  readonly googleButton: Locator;
  readonly appleButton: Locator;

  // --- Messages ---
  readonly formError: Locator;
  readonly passwordStrength: Locator;

  // --- Card ---
  readonly cardTitle: Locator;

  constructor(page: Page) {
    this.page = page;

    // Form
    this.emailInput = page.getByLabel('Email');
    this.usernameInput = page.getByLabel('Username');
    this.passwordInput = page.getByLabel('Password', { exact: true });
    this.confirmPasswordInput = page.getByLabel('Confirm Password');
    this.submitButton = page.getByRole('button', { name: /create account/i });

    // Links
    this.signInLink = page.getByRole('link', { name: /sign in/i });

    // OAuth
    this.googleButton = page.getByRole('button', { name: /google/i });
    this.appleButton = page.getByRole('button', { name: /apple/i });

    // Messages — exclude Next.js route announcer
    this.formError = page.locator('[role="alert"]:not(#__next-route-announcer__)');
    this.passwordStrength = page.getByRole('progressbar');

    // Card — shadcn CardTitle renders as <div>
    this.cardTitle = page.locator('[data-slot="card-title"]');
  }

  async goto(): Promise<void> {
    await this.page.goto('/register');
  }

  async register(email: string, username: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(password);
    await this.submitButton.click();
  }

  async registerWithDifferentPasswords(
    email: string,
    username: string,
    password: string,
    confirmPassword: string,
  ): Promise<void> {
    await this.emailInput.fill(email);
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(confirmPassword);
    await this.submitButton.click();
  }
}
