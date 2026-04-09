/**
 * Profile edit smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P1, P2, P4, P7
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ProfileEditPage, ProfileViewPage } from '../../../pages/user/profile.page';

test.describe('Profile Edit', () => {
  test('edit form renders with all fields', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const editPage = new ProfileEditPage(page);
    await editPage.goto();

    await expect(editPage.heading).toBeVisible();
    await expect(editPage.firstNameInput).toBeVisible();
    await expect(editPage.lastNameInput).toBeVisible();
    await expect(editPage.phoneInput).toBeVisible();
    await expect(editPage.bioInput).toBeVisible();
    await expect(editPage.saveButton).toBeVisible();
    await expect(editPage.cancelButton).toBeVisible();
  });

  test('edit and save profile', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const editPage = new ProfileEditPage(page);
    await editPage.goto();

    const testName = `E2E-${Date.now()}`;
    await editPage.fillProfile({
      firstName: testName,
      bio: 'E2E test bio',
    });
    await editPage.save();

    // Should redirect to profile view
    await expect(page).toHaveURL(/\/profile$/);

    // Verify data persisted — name appears in an h2 heading
    const viewPage = new ProfileViewPage(page);
    await expect(page.getByRole('heading', { name: testName, level: 2 })).toBeVisible();
  });

  test('cancel returns to profile without saving', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const editPage = new ProfileEditPage(page);
    await editPage.goto();

    await editPage.cancel();
    await expect(page).toHaveURL(/\/profile$/);
  });
});
