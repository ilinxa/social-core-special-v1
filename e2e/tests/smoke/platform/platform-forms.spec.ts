/**
 * Platform forms smoke tests.
 *
 * @layer L1
 * @system forms
 * @parameters P1, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformFormsPage } from '../../../pages/platform/platform-forms.page';

test.describe('Platform Forms', () => {
  test('forms dashboard renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const formsPage = new PlatformFormsPage(page);
    await formsPage.goto();

    await expect(formsPage.heading).toBeVisible();
  });

  test('forms dashboard shows template card', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const formsPage = new PlatformFormsPage(page);
    await formsPage.goto();

    await expect(formsPage.templatesHeading).toBeVisible();
  });
});
