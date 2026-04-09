/**
 * Business CMS Page Object Models.
 *
 * Business CMS routes are under /cconsole/{slug}/
 * All pages are wrapped in CmsBusinessGuard which shows CmsActivationPage
 * when CMS is not enabled for the business.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

// ---------------------------------------------------------------------------
// CMS Activation Page (shown by CmsBusinessGuard when CMS disabled)
// ---------------------------------------------------------------------------

export class CmsActivationPage extends BasePage {
  // State: can_request
  readonly notEnabledHeading: Locator;
  readonly requestButton: Locator;

  // State: pending
  readonly pendingHeading: Locator;
  readonly awaitingReviewBadge: Locator;

  // State: has_info_requested
  readonly actionNeededHeading: Locator;
  readonly infoRequestedBadge: Locator;

  // State: in_cooldown
  readonly deniedHeading: Locator;

  constructor(page: Page) {
    super(page);

    // can_request state
    this.notEnabledHeading = page.getByRole('heading', { name: /cms not enabled/i });
    this.requestButton = page.getByRole('button', { name: /request cms access/i });

    // pending state
    this.pendingHeading = page.getByRole('heading', { name: /request pending/i });
    this.awaitingReviewBadge = page.getByText(/awaiting review/i);

    // has_info_requested state
    this.actionNeededHeading = page.getByRole('heading', { name: /action needed/i });
    this.infoRequestedBadge = page.getByText(/information requested/i);

    // in_cooldown state
    this.deniedHeading = page.getByRole('heading', { name: /request denied/i });
  }

  async goto(businessSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/${businessSlug}`);
  }
}

// ---------------------------------------------------------------------------
// Business Sites List
// ---------------------------------------------------------------------------

export class BusinessCmsSitesPage extends BasePage {
  readonly heading: Locator;
  readonly newSiteButton: Locator;
  readonly emptyState: Locator;

  // Site create dialog
  readonly siteNameInput: Locator;
  readonly siteSlugInput: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /^sites$/i });
    this.newSiteButton = page.getByRole('button', { name: /new site/i });
    this.emptyState = page.getByText(/no sites yet/i);

    // Scoped to dialog to avoid label ambiguity
    const dialog = page.getByRole('dialog');
    this.siteNameInput = dialog.getByLabel('Name', { exact: false });
    this.siteSlugInput = dialog.getByLabel('Slug', { exact: false });
  }

  async goto(businessSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/${businessSlug}/sites`);
  }

  async clickSite(siteName: string): Promise<void> {
    await this.page.getByText(siteName, { exact: false }).click();
  }

  async createSite(data: { name: string; slug: string }): Promise<void> {
    await this.newSiteButton.click();
    await this.siteNameInput.fill(data.name);
    await this.siteSlugInput.fill(data.slug);
    await this.page.getByRole('button', { name: /create/i }).last().click();
  }
}

// ---------------------------------------------------------------------------
// Template Catalog (Browse & Activate)
// ---------------------------------------------------------------------------

export class BusinessCmsCatalogPage extends BasePage {
  readonly heading: Locator;
  readonly sectionTab: Locator;
  readonly blockTab: Locator;
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /template catalog/i });
    this.sectionTab = page.getByRole('tab', { name: /section templates/i });
    this.blockTab = page.getByRole('tab', { name: /block templates/i });
    this.emptyMessage = page.getByText(/all available .* templates are already/i);
  }

  async goto(businessSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/${businessSlug}/catalog`);
  }

  /** Click the Activate button on a template card by display name. */
  async activateTemplate(displayName: string): Promise<void> {
    // Template cards are rendered as card components — filter by text content
    const card = this.main.getByRole('article').filter({ hasText: displayName });
    await card.getByRole('button', { name: /activate/i }).click();
  }
}

// ---------------------------------------------------------------------------
// Template Library (Activated Templates)
// ---------------------------------------------------------------------------

export class BusinessCmsLibraryPage extends BasePage {
  readonly heading: Locator;
  readonly sectionTab: Locator;
  readonly blockTab: Locator;
  readonly emptyMessage: Locator;

  // Remove confirmation dialog
  readonly removeConfirmButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /my templates/i });
    this.sectionTab = page.getByRole('tab', { name: /section templates/i });
    this.blockTab = page.getByRole('tab', { name: /block templates/i });
    this.emptyMessage = page.getByText(/no .* templates activated/i);

    this.removeConfirmButton = page
      .getByRole('alertdialog')
      .getByRole('button', { name: /remove/i });
  }

  async goto(businessSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/${businessSlug}/library`);
  }

  /** Click the Remove button on a template card by display name. */
  async removeTemplate(displayName: string): Promise<void> {
    // Template cards are rendered as card components — filter by text content
    const card = this.main.getByRole('article').filter({ hasText: displayName });
    await card.getByRole('button', { name: /remove/i }).click();
  }
}
