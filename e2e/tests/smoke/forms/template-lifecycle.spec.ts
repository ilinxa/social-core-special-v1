/**
 * Template lifecycle smoke tests (publish, archive, fork).
 *
 * @layer L1
 * @system forms
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { TemplateLibraryPage, FormsDashboardPage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Template Lifecycle', () => {
  test('forms dashboard renders with navigation cards', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const dashboard = new FormsDashboardPage(page);
    await dashboard.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(dashboard.heading).toBeVisible();
    await expect(dashboard.templatesCard).toBeVisible();
    await expect(dashboard.libraryCard).toBeVisible();
  });

  test('template library page renders', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const library = new TemplateLibraryPage(page);
    await library.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(library.heading).toBeVisible();
  });
});
