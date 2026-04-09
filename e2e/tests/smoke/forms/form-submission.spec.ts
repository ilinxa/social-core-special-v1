/**
 * Form submission smoke tests.
 *
 * @layer L1
 * @system forms
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { FormResponsesPage } from '../../../pages/forms/forms.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Form Submission', () => {
  test('responses page renders with form selector', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const responsesPage = new FormResponsesPage(page);
    await responsesPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(responsesPage.heading).toBeVisible();
  });

  test('responses page shows select form prompt', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const responsesPage = new FormResponsesPage(page);
    await responsesPage.gotoForBusiness(E2E_BUSINESS.slug);

    await expect(responsesPage.selectFormMessage).toBeVisible();
  });
});
