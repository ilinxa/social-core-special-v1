/**
 * Platform CMS Page Object Models.
 *
 * Sites route:      /cconsole/sites
 * Templates route:  /cconsole/templates
 * Businesses route: /cconsole/businesses
 * Media route:      /cconsole/media
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

// ---------------------------------------------------------------------------
// Sites List
// ---------------------------------------------------------------------------

export class PlatformCmsSitesPage extends BasePage {
  readonly heading: Locator;
  readonly newSiteButton: Locator;
  readonly emptyState: Locator;

  // Site create dialog
  readonly dialogTitle: Locator;
  readonly siteNameInput: Locator;
  readonly siteSlugInput: Locator;
  readonly siteDomainInput: Locator;
  readonly siteDescriptionInput: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /^sites$/i });
    this.newSiteButton = page.getByRole('button', { name: /new site/i });
    this.emptyState = page.getByText(/no sites yet/i);

    // Dialog fields — scoped to dialog to avoid label ambiguity with edit forms
    // Labels: "Name", "Slug", "Domain (optional)", "Description (optional)"
    const dialog = page.getByRole('dialog');
    this.dialogTitle = dialog.getByRole('heading', { name: /create site/i });
    this.siteNameInput = dialog.getByLabel('Name', { exact: false });
    this.siteSlugInput = dialog.getByLabel('Slug', { exact: false });
    this.siteDomainInput = dialog.getByLabel('Domain', { exact: false });
    this.siteDescriptionInput = dialog.getByLabel('Description', { exact: false });
  }

  async goto(): Promise<void> {
    await this.page.goto('/cconsole/sites');
  }

  /** Click a site row by name to navigate to site detail. */
  async clickSite(siteName: string): Promise<void> {
    await this.page.getByText(siteName, { exact: false }).first().click();
  }

  /** Open the create site dialog and fill the form. */
  async createSite(data: {
    name: string;
    slug: string;
    domain?: string;
    description?: string;
  }): Promise<void> {
    await this.newSiteButton.click();
    await this.siteNameInput.fill(data.name);
    await this.siteSlugInput.fill(data.slug);
    if (data.domain) await this.siteDomainInput.fill(data.domain);
    if (data.description) await this.siteDescriptionInput.fill(data.description);
    const responsePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/sites/') && resp.request().method() === 'POST',
      { timeout: 10000 },
    ).catch(() => null);
    await this.page.getByRole('dialog').getByRole('button', { name: /create/i }).click();
    await responsePromise;
  }

  /** Get the number of site rows visible in the list. */
  getSiteRows(): Locator {
    return this.main.getByRole('button').filter({ hasText: /.+/ });
  }
}

// ---------------------------------------------------------------------------
// Templates Browser
// ---------------------------------------------------------------------------

export class PlatformCmsTemplatesPage extends BasePage {
  readonly heading: Locator;
  readonly sectionTab: Locator;
  readonly blockTab: Locator;
  readonly emptyState: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /^templates$/i });
    this.sectionTab = page.getByRole('tab', { name: /section templates/i });
    this.blockTab = page.getByRole('tab', { name: /block templates/i });
    this.emptyState = page.getByText(/no .* templates/i);
  }

  async goto(): Promise<void> {
    await this.page.goto('/cconsole/templates');
  }
}

// ---------------------------------------------------------------------------
// Business CMS Management (Platform Admin)
// ---------------------------------------------------------------------------

export class PlatformCmsBusinessesPage extends BasePage {
  readonly heading: Locator;
  readonly emptyState: Locator;
  readonly activationsSheetTitle: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', {
      level: 1,
      name: /business cms management/i,
    });
    this.emptyState = page.getByText(/no businesses found/i);
    this.activationsSheetTitle = page.getByRole('heading', {
      name: /activated templates/i,
    });
  }

  async goto(): Promise<void> {
    await this.page.goto('/cconsole/businesses');
  }

  /** Get the toggle switch for a business by its legal name. */
  getBusinessToggle(businessName: string): Locator {
    // Find the button containing the business name, go to parent row, then find switch
    return this.page
      .getByRole('button', { name: new RegExp(businessName, 'i') })
      .locator('..')
      .getByRole('switch');
  }

  /** Click a business row to open the activations sheet. */
  async clickBusiness(businessName: string): Promise<void> {
    await this.page
      .getByRole('button', { name: new RegExp(businessName, 'i') })
      .click();
  }
}

// ---------------------------------------------------------------------------
// API Keys (Platform — global landing page)
// ---------------------------------------------------------------------------

export class PlatformCmsApiKeysPage extends BasePage {
  readonly heading: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /api keys/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/cconsole/api-keys');
  }
}

// ---------------------------------------------------------------------------
// Media Library (Platform)
// ---------------------------------------------------------------------------

export class PlatformMediaPage extends BasePage {
  readonly heading: Locator;
  readonly uploadButton: Locator;
  readonly gridViewButton: Locator;
  readonly listViewButton: Locator;
  readonly emptyState: Locator;
  readonly deleteButton: Locator;
  readonly deleteConfirmButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /media library/i });
    this.uploadButton = page.getByRole('button', { name: /upload/i });
    this.gridViewButton = page.getByRole('button', { name: /grid/i }).first();
    this.listViewButton = page.getByRole('button', { name: /list/i }).first();
    this.emptyState = page.getByText(/no media files yet/i);
    this.deleteButton = page.getByRole('button', { name: /delete/i });
    this.deleteConfirmButton = page
      .getByRole('alertdialog')
      .getByRole('button', { name: /delete/i });
  }

  async goto(): Promise<void> {
    await this.page.goto('/cconsole/media');
  }
}
