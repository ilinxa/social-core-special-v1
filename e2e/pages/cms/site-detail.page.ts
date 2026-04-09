/**
 * CMS Site Detail Page Object Model.
 *
 * Platform route:  /cconsole/sites/{siteSlug}
 * Business route:  /cconsole/{slug}/sites/{siteSlug}
 *
 * Contains site info header, edit form, and tabs (Pages + API Keys).
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class CmsSiteDetailPage extends BasePage {
  // Header
  readonly siteName: Locator;
  readonly statusBadge: Locator;

  // Action buttons (permission-gated)
  readonly editButton: Locator;
  readonly deleteButton: Locator;

  // Edit mode form
  readonly editNameInput: Locator;
  readonly editDomainInput: Locator;
  readonly editDescriptionInput: Locator;
  readonly saveButton: Locator;
  readonly cancelButton: Locator;

  // Tabs
  readonly pagesTab: Locator;
  readonly apiKeysTab: Locator;

  // Pages list (inside Pages tab)
  readonly newPageButton: Locator;
  readonly pagesHeading: Locator;

  // Page create dialog
  readonly pageTitleInput: Locator;
  readonly pageSlugInput: Locator;
  readonly pagePathInput: Locator;
  readonly pageOrderInput: Locator;

  // Status filter buttons (page list)
  readonly allStatusButton: Locator;
  readonly draftStatusButton: Locator;
  readonly publishedStatusButton: Locator;
  readonly archivedStatusButton: Locator;

  // Delete confirmation
  readonly deleteConfirmButton: Locator;

  constructor(page: Page) {
    super(page);

    // Header elements
    this.siteName = page.getByRole('heading', { level: 1 });
    this.statusBadge = page.getByText(/^(active|inactive)$/i).first();

    // Action buttons
    this.editButton = page.getByRole('button', { name: /edit/i }).first();
    this.deleteButton = page.getByRole('button', { name: /delete/i }).first();

    // Edit form — labels match frontend <Label htmlFor="edit-name"> etc.
    this.editNameInput = page.getByLabel('Name', { exact: false });
    this.editDomainInput = page.getByLabel('Domain', { exact: false });
    this.editDescriptionInput = page.getByLabel('Description', { exact: false });
    this.saveButton = page.getByRole('button', { name: /save/i });
    this.cancelButton = page.getByRole('button', { name: /cancel/i });

    // Tabs
    this.pagesTab = page.getByRole('tab', { name: /pages/i });
    this.apiKeysTab = page.getByRole('tab', { name: /api keys/i });

    // Pages list
    this.newPageButton = page.getByRole('button', { name: /new page/i });
    this.pagesHeading = page.getByRole('heading', { name: /^pages$/i });

    // Page create dialog fields — scoped to dialog to avoid label ambiguity
    // Labels: "Title", "Slug", "Path", "Order"
    const dialog = page.getByRole('dialog');
    this.pageTitleInput = dialog.getByLabel('Title', { exact: false });
    this.pageSlugInput = dialog.getByLabel('Slug', { exact: false });
    this.pagePathInput = dialog.getByLabel('Path', { exact: false });
    this.pageOrderInput = dialog.getByLabel('Order', { exact: false });

    // Status filter buttons
    this.allStatusButton = page.getByRole('button', { name: /^all$/i });
    this.draftStatusButton = page.getByRole('button', { name: /^draft$/i });
    this.publishedStatusButton = page.getByRole('button', { name: /^published$/i });
    this.archivedStatusButton = page.getByRole('button', { name: /^archived$/i });

    // Delete confirmation
    this.deleteConfirmButton = page
      .getByRole('dialog')
      .getByRole('button', { name: /delete/i });
  }

  async gotoForPlatform(siteSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/sites/${siteSlug}`);
  }

  async gotoForBusiness(businessSlug: string, siteSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/${businessSlug}/sites/${siteSlug}`);
  }

  /** Click a page row by title to navigate to the page editor. */
  async clickPage(pageTitle: string): Promise<void> {
    await this.page.getByText(pageTitle, { exact: false }).click();
  }

  /** Open the create page dialog and fill the form. */
  async createPage(data: {
    title: string;
    slug: string;
    path: string;
    order?: number;
  }): Promise<void> {
    await this.newPageButton.click();
    await this.pageTitleInput.fill(data.title);
    await this.pageSlugInput.fill(data.slug);
    await this.pagePathInput.fill(data.path);
    if (data.order !== undefined) {
      await this.pageOrderInput.fill(String(data.order));
    }
    const responsePromise = this.page.waitForResponse(
      (resp) => resp.url().includes('/pages/') && resp.request().method() === 'POST',
      { timeout: 10000 },
    ).catch(() => null);
    await this.page.getByRole('dialog').getByRole('button', { name: /create page/i }).click();
    await responsePromise;
  }
}
