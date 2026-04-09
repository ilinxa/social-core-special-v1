/**
 * Settings smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P1, P2, P14
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { SettingsPage } from '../../../pages/user/settings.page';
import { checkLandmarks, checkFormLabels } from '../../../lib/a11y-checks';

test.describe('Settings', () => {
  test('settings page renders with username section', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();

    await expect(settingsPage.usernameInput).toBeVisible();
    await expect(settingsPage.updateUsernameButton).toBeVisible();
  });

  test('danger zone with deactivate button is visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();

    await expect(settingsPage.deactivateButton).toBeVisible();
  });

  test('deactivate dialog requires typing confirmation', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();

    await settingsPage.initiateDeactivation();

    // Dialog should appear with disabled confirm button
    await expect(settingsPage.deactivateConfirmInput).toBeVisible();
    await expect(settingsPage.deactivateConfirmButton).toBeDisabled();

    // Type "deactivate" to enable the button
    await settingsPage.deactivateConfirmInput.fill('deactivate');
    await expect(settingsPage.deactivateConfirmButton).toBeEnabled();

    // Cancel instead of confirming
    await settingsPage.deactivateCancelButton.click();
  });

  // --- Visual Regression ---
  test('settings page visual regression', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await expect(page).toHaveScreenshot('settings-page.png');
  });

  // --- Accessibility ---
  test('settings page has correct ARIA landmarks', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await checkLandmarks(page);
  });

  test('settings form inputs have associated labels', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    const form = page.locator('form').first();
    await checkFormLabels(page, form);
  });
});
