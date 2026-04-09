/**
 * CMS API Keys Page Object Model.
 *
 * API Keys are rendered as a tab within the Site Detail page.
 * This POM targets the API Key Management panel content.
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

export class ApiKeysPanel extends BasePage {
  readonly heading: Locator;
  readonly createKeyButton: Locator;
  readonly emptyState: Locator;

  // Create dialog
  readonly createDialogTitle: Locator;
  readonly keyNameInput: Locator;
  readonly keyRateInput: Locator;

  // Key reveal dialog (one-time display)
  readonly revealDialogTitle: Locator;
  readonly revealedKey: Locator;
  readonly copyButton: Locator;

  // Revoke confirmation dialog
  readonly revokeDialogTitle: Locator;
  readonly revokeConfirmButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { name: /^api keys$/i });
    this.createKeyButton = page.getByRole('button', { name: /create key/i });
    this.emptyState = page.getByText(/no api keys yet/i);

    // Create dialog — scoped to dialog to avoid "Name" label ambiguity
    // Labels: "Name", "Rate Limit (req/min)"
    const createDialog = page.getByRole('dialog');
    this.createDialogTitle = createDialog.getByRole('heading', { name: /create api key/i });
    this.keyNameInput = createDialog.getByLabel('Name', { exact: false });
    this.keyRateInput = createDialog.getByLabel('Rate', { exact: false });

    // Reveal dialog — key shown in <code> block inside the dialog
    // <code> has no ARIA role; scoping to dialog + using tag is the accepted fallback
    this.revealDialogTitle = page.getByRole('heading', { name: /api key created/i });
    this.revealedKey = page.getByRole('dialog').getByText(/^cmsk_/);
    this.copyButton = page
      .getByRole('dialog')
      .getByRole('button', { name: /copy/i });

    // Revoke
    this.revokeDialogTitle = page.getByRole('heading', { name: /revoke api key/i });
    this.revokeConfirmButton = page
      .getByRole('dialog')
      .getByRole('button', { name: /revoke/i });
  }

  /** Create an API key via the dialog. */
  async createKey(name: string, rateLimit?: number): Promise<void> {
    await this.createKeyButton.click();
    await this.keyNameInput.fill(name);
    if (rateLimit !== undefined) {
      await this.keyRateInput.fill(String(rateLimit));
    }
    await this.page.getByRole('button', { name: /create/i }).last().click();
  }

  /** Get the key row containing the given name. */
  getKeyRow(keyName: string): Locator {
    // Each key row is a container element; filter by text content
    return this.page.getByRole('listitem').filter({ hasText: keyName });
  }

  /** Click Revoke on a key row by name. */
  async revokeKey(keyName: string): Promise<void> {
    // API key rows are rendered in a list — find the row containing the key name
    // and click the revoke button within it
    const row = this.getKeyRow(keyName);
    await row.getByRole('button', { name: /revoke/i }).click();
  }
}
