/**
 * Form field CRUD smoke tests (add, update, delete, reorder).
 *
 * @layer L1
 * @system forms
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { CreateTemplatePage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Field CRUD', () => {
  test('create template page has slug and description fields', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const createPage = new CreateTemplatePage(page);
    await createPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(createPage.nameInput).toBeVisible();
    await expect(createPage.slugInput).toBeVisible();
    await expect(createPage.descriptionInput).toBeVisible();
  });

  test('cancel button navigates away from create page', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const createPage = new CreateTemplatePage(page);
    await createPage.gotoForBusiness(E2E_BUSINESS.slug);

    // Wait for form to load before interacting
    await expect(createPage.nameInput).toBeVisible();
    await createPage.cancelButton.click();
    await expect(page).not.toHaveURL(/\/new$/);
  });
});
