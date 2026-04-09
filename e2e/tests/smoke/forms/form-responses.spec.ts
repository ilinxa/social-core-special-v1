/**
 * Form responses list smoke tests.
 *
 * @layer L1
 * @system forms
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { FormResponsesPage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Form Responses', () => {
  test('responses page has back button', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const responsesPage = new FormResponsesPage(page);
    await responsesPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(responsesPage.heading).toBeVisible();
    await expect(responsesPage.backButton).toBeVisible();
  });

  test('responses page shows empty state without form selected', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const responsesPage = new FormResponsesPage(page);
    await responsesPage.gotoForBusiness(E2E_BUSINESS.slug);

    // Without a form selected, show the selection prompt
    await expect(responsesPage.selectFormMessage).toBeVisible();
  });
});
