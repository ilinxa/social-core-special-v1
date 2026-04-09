/**
 * Form template builder smoke tests.
 *
 * @layer L1
 * @system forms
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { CreateTemplatePage, TemplateListPage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Template Builder', () => {
  test('create template page renders with form fields', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const createPage = new CreateTemplatePage(page);
    await createPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(createPage.heading).toBeVisible();
    await expect(createPage.nameInput).toBeVisible();
    await expect(createPage.createFormButton).toBeVisible();
    await expect(createPage.cancelButton).toBeVisible();
  });

  test('create form button is disabled when name is empty', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const createPage = new CreateTemplatePage(page);
    await createPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(createPage.createFormButton).toBeDisabled();
  });

  test('template list page renders with status tabs', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const listPage = new TemplateListPage(page);
    await listPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(listPage.heading).toBeVisible();
    await expect(listPage.allTab).toBeVisible();
    await expect(listPage.draftTab).toBeVisible();
    await expect(listPage.activeTab).toBeVisible();
  });
});
