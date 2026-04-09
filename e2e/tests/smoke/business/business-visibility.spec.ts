/**
 * Business visibility settings smoke tests.
 *
 * @layer L1
 * @system visibility
 * @parameters P1, P5, P7
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import {
  BusinessProfileEditPage,
} from '../../../pages/business/business-console.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Visibility', () => {
  test('profile edit page renders with tabs', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const profileEdit = new BusinessProfileEditPage(page);
    await profileEdit.goto(E2E_BUSINESS.slug);

    await expect(profileEdit.heading).toBeVisible();
    await expect(profileEdit.editTab).toBeVisible();
    await expect(profileEdit.previewTab).toBeVisible();
  });

  test('profile edit form has name and description fields', async ({
    businessOwnerPage,
  }) => {
    const page = businessOwnerPage;
    const profileEdit = new BusinessProfileEditPage(page);
    await profileEdit.goto(E2E_BUSINESS.slug);

    await expect(profileEdit.displayNameInput).toBeVisible();
    await expect(profileEdit.descriptionInput).toBeVisible();
  });

  test('save button is present on edit form', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const profileEdit = new BusinessProfileEditPage(page);
    await profileEdit.goto(E2E_BUSINESS.slug);

    await expect(profileEdit.saveButton).toBeVisible();
  });
});
