/**
 * Forms Page Object Models.
 *
 * Dashboard route: /bconsole/[slug]/forms | /pconsole/forms
 * Templates route: .../forms/templates
 * Create route: .../forms/templates/new
 * Detail route: .../forms/templates/[id]
 * Responses route: .../forms/responses
 * Library route: .../forms/library
 */

import type { Page, Locator } from '@playwright/test';
import { BasePage } from '../base.page';

/** Forms dashboard — card grid (Templates, Library, Responses). */
export class FormsDashboardPage extends BasePage {
  readonly heading: Locator;
  readonly templatesCard: Locator;
  readonly libraryCard: Locator;
  readonly responsesCard: Locator;
  readonly createNewFormButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /^forms$/i });
    // Cards use CardTitle which renders as <div>, not heading
    this.templatesCard = page.locator('[data-slot="card-title"]').filter({ hasText: /^templates$/i });
    this.libraryCard = page.locator('[data-slot="card-title"]').filter({ hasText: /^library$/i });
    this.responsesCard = page.locator('[data-slot="card-title"]').filter({ hasText: /^responses$/i });
    this.createNewFormButton = page.getByRole('button', { name: /create new form/i });
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/forms');
  }
}

/** Template list page — status tabs + template rows. */
export class TemplateListPage extends BasePage {
  readonly heading: Locator;
  readonly backButton: Locator;
  readonly newFormButton: Locator;

  // --- Status tabs ---
  readonly allTab: Locator;
  readonly activeTab: Locator;
  readonly draftTab: Locator;
  readonly archivedTab: Locator;

  // --- Empty state ---
  readonly emptyMessage: Locator;

  // --- Pagination ---
  readonly previousButton: Locator;
  readonly nextButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /form templates/i });
    this.backButton = page.getByRole('button', { name: /back/i });
    this.newFormButton = page.getByRole('button', { name: /new form/i });

    // Status tabs
    this.allTab = page.getByRole('button', { name: /^all$/i });
    this.activeTab = page.getByRole('button', { name: /^active$/i });
    this.draftTab = page.getByRole('button', { name: /^draft$/i });
    this.archivedTab = page.getByRole('button', { name: /^archived$/i });

    // Empty state
    this.emptyMessage = page.getByText(/no templates found/i);

    // Pagination
    this.previousButton = page.getByRole('button', { name: /previous/i });
    this.nextButton = page.getByRole('button', { name: /^next$/i });
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms/templates`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/forms/templates');
  }
}

/** Create new template page — name, slug, description form. */
export class CreateTemplatePage extends BasePage {
  readonly heading: Locator;
  readonly backButton: Locator;

  // --- Form fields ---
  readonly nameInput: Locator;
  readonly slugInput: Locator;
  readonly descriptionInput: Locator;

  // --- Buttons ---
  readonly createFormButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /create new form/i });
    this.backButton = page.getByRole('button', { name: /back/i });

    // Form fields
    this.nameInput = page.getByLabel(/form name/i);
    this.slugInput = page.getByLabel(/slug/i);
    this.descriptionInput = page.getByLabel(/description/i);

    // Buttons
    this.createFormButton = page.getByRole('button', { name: /create form/i });
    this.cancelButton = page.getByRole('button', { name: /cancel/i });
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms/templates/new`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/forms/templates/new');
  }
}

/** Template detail page — view/edit template with form builder. */
export class TemplateDetailPage extends BasePage {
  readonly backButton: Locator;

  // --- Action buttons ---
  readonly publishButton: Locator;
  readonly editButton: Locator;
  readonly archiveButton: Locator;
  readonly restoreButton: Locator;
  readonly deleteButton: Locator;

  // --- Form builder (design mode) ---
  readonly addFieldHeading: Locator;
  readonly fieldKeyInput: Locator;
  readonly fieldTypeSelect: Locator;
  readonly fieldLabelInput: Locator;
  readonly addFieldButton: Locator;

  // --- Move controls ---
  readonly moveUpButton: Locator;
  readonly moveDownButton: Locator;

  constructor(page: Page) {
    super(page);
    this.backButton = page.getByRole('button', { name: /back/i });

    // Actions
    this.publishButton = page.getByRole('button', { name: /^publish$/i });
    this.editButton = page.getByRole('button', { name: /^edit/i });
    this.archiveButton = page.getByRole('button', { name: /^archive$/i });
    this.restoreButton = page.getByRole('button', { name: /restore to draft/i });
    this.deleteButton = page.getByRole('button', { name: /^delete$/i });

    // Add field panel
    this.addFieldHeading = page.getByText(/add field/i);
    this.fieldKeyInput = page.getByLabel(/field key/i);
    this.fieldTypeSelect = page.getByLabel(/field type/i);
    this.fieldLabelInput = page.getByLabel(/^label$/i);
    this.addFieldButton = page.getByRole('button', { name: /^add field$/i });

    // Move controls
    this.moveUpButton = page.getByRole('button', { name: /move field up/i });
    this.moveDownButton = page.getByRole('button', { name: /move field down/i });
  }

  async gotoForBusiness(slug: string, templateId: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms/templates/${templateId}`);
  }

  async gotoForPlatform(templateId: string): Promise<void> {
    await this.page.goto(`/pconsole/forms/templates/${templateId}`);
  }
}

/** Form responses page — form selector + response table. */
export class FormResponsesPage extends BasePage {
  readonly heading: Locator;
  readonly backButton: Locator;

  // --- Form selector ---
  readonly formSelect: Locator;

  // --- Status tabs ---
  readonly allTab: Locator;
  readonly submittedTab: Locator;
  readonly draftTab: Locator;
  readonly processedTab: Locator;
  readonly voidTab: Locator;

  // --- Empty state ---
  readonly selectFormMessage: Locator;
  readonly noResponsesMessage: Locator;

  // --- Pagination ---
  readonly previousButton: Locator;
  readonly nextButton: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /form responses/i });
    this.backButton = page.getByRole('button', { name: /back/i });

    // Form selector
    this.formSelect = page.getByRole('combobox', { name: /select form/i });

    // Status tabs
    this.allTab = page.getByRole('button', { name: /^all$/i });
    this.submittedTab = page.getByRole('button', { name: /^submitted$/i });
    this.draftTab = page.getByRole('button', { name: /^draft$/i });
    this.processedTab = page.getByRole('button', { name: /^processed$/i });
    this.voidTab = page.getByRole('button', { name: /^void$/i });

    // Empty states
    this.selectFormMessage = page.getByText(/select a form to view/i);
    this.noResponsesMessage = page.getByText(/no responses found/i);

    // Pagination
    this.previousButton = page.getByRole('button', { name: /previous/i });
    this.nextButton = page.getByRole('button', { name: /^next$/i });
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms/responses`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/forms/responses');
  }
}

/** Template library page — public templates + fork. */
export class TemplateLibraryPage extends BasePage {
  readonly heading: Locator;
  readonly backButton: Locator;
  readonly emptyMessage: Locator;

  constructor(page: Page) {
    super(page);
    this.heading = page.getByRole('heading', { level: 1, name: /template library/i });
    this.backButton = page.getByRole('button', { name: /back/i });
    this.emptyMessage = page.getByText(/no public templates available/i);
  }

  /** Get a fork button (nth = 0-based index when multiple templates). */
  getForkButton(nth = 0): Locator {
    return this.page.getByRole('button', { name: /^fork$/i }).nth(nth);
  }

  async gotoForBusiness(slug: string): Promise<void> {
    await this.page.goto(`/bconsole/${slug}/forms/library`);
  }

  async gotoForPlatform(): Promise<void> {
    await this.page.goto('/pconsole/forms/library');
  }
}
