/**
 * CMS Page Editor Page Object Model.
 *
 * Route: .../sites/{siteSlug}/pages/{pageSlug}
 * Contains content tree, block editor, publish controls, version history.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class PageEditorPage extends BasePage {
  // Header
  readonly pageTitle: Locator;
  readonly statusBadge: Locator;
  readonly backButton: Locator;

  // Action buttons
  readonly publishButton: Locator;
  readonly unpublishButton: Locator;
  readonly historyButton: Locator;
  readonly exportButton: Locator;
  readonly importButton: Locator;

  // Content tree
  readonly contentTree: Locator;
  readonly noSelectionMessage: Locator;

  // Block editor
  readonly saveStatusSaving: Locator;
  readonly saveStatusSaved: Locator;
  readonly saveStatusError: Locator;
  readonly schemaWarning: Locator;
  readonly noFieldsMessage: Locator;

  // Publish / Unpublish confirmation dialogs
  readonly publishConfirmButton: Locator;
  readonly unpublishConfirmButton: Locator;

  // Publish errors
  readonly publishErrorBanner: Locator;

  // Version history panel (Sheet)
  readonly historyTitle: Locator;
  readonly historyEmptyState: Locator;

  // Import file input
  readonly importFileInput: Locator;

  constructor(page: Page) {
    super(page);

    // Header
    this.pageTitle = page.getByRole('heading', { level: 1 }).first();
    this.statusBadge = page.getByText(/^(draft|published|archived)$/i).first();
    this.backButton = page.getByRole('button', { name: /back/i }).first();

    // Action buttons
    this.publishButton = page.getByRole('button', { name: /^publish$/i });
    this.unpublishButton = page.getByRole('button', { name: /^unpublish$/i });
    this.historyButton = page.getByRole('button', { name: /history/i });
    this.exportButton = page.getByRole('button', { name: /export/i });
    this.importButton = page.getByRole('button', { name: /import/i });

    // Content tree (ARIA tree role)
    this.contentTree = page.getByRole('tree', { name: /page content structure/i });
    this.noSelectionMessage = page.getByText(
      /select a block from the tree to edit/i,
    );

    // Block editor save status (aria-live="polite")
    this.saveStatusSaving = page.getByText(/^saving\.\.\.$/i);
    this.saveStatusSaved = page.getByText(/^saved$/i);
    this.saveStatusError = page.getByText(/^error saving$/i);

    // Schema version mismatch warning
    this.schemaWarning = page.getByText(/version mismatch/i);

    // No fields
    this.noFieldsMessage = page.getByText(/no fields defined/i);

    // Confirmation dialogs
    this.publishConfirmButton = page
      .getByRole('dialog')
      .getByRole('button', { name: /^publish$/i });
    this.unpublishConfirmButton = page
      .getByRole('dialog')
      .getByRole('button', { name: /^unpublish$/i });

    // Publish error banner
    this.publishErrorBanner = page.getByText(/validation error/i);

    // Version history
    this.historyTitle = page.getByRole('heading', { name: /version history/i });
    this.historyEmptyState = page.getByText(/no versions recorded yet/i);

    // Import — file inputs have no ARIA role; hidden inputs triggered by the Import button
    // This is the accepted fallback per CLAUDE.md priority 5 (no semantic selector exists)
    this.importFileInput = page.getByTestId('import-file-input').or(
      page.locator('input[type="file"]'),
    );
  }

  async gotoForPlatform(siteSlug: string, pageSlug: string): Promise<void> {
    await this.page.goto(`/cconsole/sites/${siteSlug}/pages/${pageSlug}`);
  }

  async gotoForBusiness(
    businessSlug: string,
    siteSlug: string,
    pageSlug: string,
  ): Promise<void> {
    await this.page.goto(
      `/cconsole/${businessSlug}/sites/${siteSlug}/pages/${pageSlug}`,
    );
  }

  /** Click a block node in the content tree by its label text. */
  async clickBlock(blockLabel: string): Promise<void> {
    await this.contentTree.getByText(blockLabel, { exact: false }).click();
  }

  /** Get the version rows in the history panel. */
  getVersionRows(): Locator {
    return this.page.getByText(/^v\d+$/i);
  }

  /** Click restore on a specific version in the history panel. */
  async restoreVersion(versionText: string): Promise<void> {
    // Version rows are rendered as list items — filter by version text
    const row = this.page
      .getByRole('listitem')
      .filter({ hasText: versionText });
    await row.getByRole('button', { name: /restore/i }).click();
  }
}
