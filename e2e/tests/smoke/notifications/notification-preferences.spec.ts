/**
 * @layer L1
 * @system notifications
 * @parameters P1, P2, P3, P5
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { NotificationPreferencesSection } from '../../../pages/notifications/notifications.page';
import { isSystemEnabled } from '../../../lib/feature-gates';

test.describe('Notification Preferences', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('settings page shows notification preferences section', async ({
    authenticatedPage,
  }) => {
    const prefsSection = new NotificationPreferencesSection(authenticatedPage);
    await prefsSection.goto();

    await expect(prefsSection.sectionHeading).toBeVisible();
    await expect(prefsSection.sectionDescription).toBeVisible();
  });

  test('category cards render for all 5 categories', async ({
    authenticatedPage,
  }) => {
    const prefsSection = new NotificationPreferencesSection(authenticatedPage);
    await prefsSection.goto();

    await expect(prefsSection.authCategory).toBeVisible();
    await expect(prefsSection.securityCategory).toBeVisible();
    await expect(prefsSection.transactionsCategory).toBeVisible();
    await expect(prefsSection.marketingCategory).toBeVisible();
    await expect(prefsSection.socialCategory).toBeVisible();
  });

  test('toggle preference switch works', async ({ authenticatedPage }) => {
    const prefsSection = new NotificationPreferencesSection(authenticatedPage);
    await prefsSection.goto();

    // Toggle "New Login Alert" email switch
    const emailSwitch = prefsSection.getEmailSwitch('New Login Alert');
    await expect(emailSwitch).toBeVisible();
    await emailSwitch.click();

    // No error toast should appear
    await expect(
      authenticatedPage.locator('[data-sonner-toast]').filter({ hasText: /failed/i }),
    ).not.toBeVisible({ timeout: 3000 });
  });

  test('non-configurable types show lock icon', async ({
    authenticatedPage,
  }) => {
    const prefsSection = new NotificationPreferencesSection(authenticatedPage);
    await prefsSection.goto();

    // Lock icon indicates non-configurable types (verify_email, welcome, etc.)
    await expect(prefsSection.getLockIcon().first()).toBeVisible();
  });

  test('reset preference button triggers toast', async ({
    authenticatedPage,
  }) => {
    const prefsSection = new NotificationPreferencesSection(authenticatedPage);
    await prefsSection.goto();

    // Reset "New Login Alert" preference
    const resetButton = prefsSection.getResetButton('New Login Alert');
    await expect(resetButton).toBeVisible();
    await resetButton.click();

    // Should show success toast
    await expect(
      authenticatedPage.locator('[data-sonner-toast]').filter({ hasText: /reset to default/i }),
    ).toBeVisible();
  });
});
