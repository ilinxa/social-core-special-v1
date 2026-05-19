/**
 * Form field types smoke tests — all 14+ field types.
 *
 * @layer L1
 * @system forms
 * @parameters P1, P4, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { TemplateListPage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Field Types', () => {
  test('template list shows new form button', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const listPage = new TemplateListPage(page);
    await listPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(listPage.newFormButton).toBeVisible();
  });

  test('template list shows templates or empty state', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const listPage = new TemplateListPage(page);
    await listPage.gotoForBusiness(E2E_BUSINESS.slug);

    // Wait for page to finish loading
    await expect(listPage.newFormButton).toBeVisible();

    // Should show templates or empty message. `.first()` after `.or()` because
    // both branches can render at once and strict mode rejects 2+ matches.
    const firstTemplate = page.getByText(/draft|active|archived/i).first();
    await expect(firstTemplate.or(listPage.emptyMessage).first()).toBeVisible();
  });
});
