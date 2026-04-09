/**
 * Public Pages Object Model — landing, about, contact.
 *
 * Routes: /, /about, /contact
 * These are public pages accessible without authentication.
 */

import type { Page, Locator } from '@playwright/test';

export class LandingPage {
  readonly page: Page;

  // --- Header (public variant) ---
  readonly brandLink: Locator;
  readonly exploreLink: Locator;
  readonly aboutLink: Locator;
  readonly contactLink: Locator;
  readonly signInButton: Locator;
  readonly registerButton: Locator;
  readonly mobileMenuButton: Locator;

  // --- Landing content ---
  readonly heading: Locator;
  readonly signInLink: Locator;

  constructor(page: Page) {
    this.page = page;

    // Public header nav
    this.brandLink = page.getByRole('link', { name: /socialmedia adv/i });
    this.exploreLink = page.getByRole('link', { name: /explore/i }).first();
    this.aboutLink = page.getByRole('link', { name: /about/i }).first();
    this.contactLink = page.getByRole('link', { name: /contact/i }).first();
    this.signInButton = page.getByRole('link', { name: /sign in/i }).first();
    this.registerButton = page.getByRole('link', { name: /register/i }).first();
    this.mobileMenuButton = page.getByLabel(/open navigation menu/i);

    // Landing page content
    this.heading = page.getByRole('heading', { level: 1 });
    this.signInLink = page.getByRole('link', { name: /sign in/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/');
  }
}

export class AboutPage {
  readonly page: Page;
  readonly heading: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1, name: /about/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/about');
  }
}

export class ContactPage {
  readonly page: Page;
  readonly heading: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1, name: /contact/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/contact');
  }
}
