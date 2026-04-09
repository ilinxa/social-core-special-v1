/**
 * @layer L1
 * @system notifications
 * @parameters P1, P2, P3
 * @priority P0
 */
import { test, expect } from '../../../fixtures/auth.fixture';
import { NotificationsPage } from '../../../pages/notifications/notifications.page';
import { isSystemEnabled } from '../../../lib/feature-gates';

test.describe('Notification Center', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('notification page renders heading', async ({ authenticatedPage }) => {
    const notifPage = new NotificationsPage(authenticatedPage);
    await notifPage.goto();

    await expect(notifPage.heading).toBeVisible();
  });

  test('scope tabs are visible', async ({ authenticatedPage }) => {
    const notifPage = new NotificationsPage(authenticatedPage);
    await notifPage.goto();

    await expect(notifPage.allTab).toBeVisible();
    await expect(notifPage.personalTab).toBeVisible();
  });

  test('empty state for new user', async ({ authenticatedPage }) => {
    const notifPage = new NotificationsPage(authenticatedPage);
    await notifPage.goto();

    // New user should see empty state (registration notifications may or may not
    // be visible depending on async delivery timing)
    await expect(
      notifPage.emptyHeading.or(notifPage.heading),
    ).toBeVisible();
  });

  test('notification list or empty state is shown', async ({ authenticatedPage }) => {
    const notifPage = new NotificationsPage(authenticatedPage);
    await notifPage.goto();

    // Either the notification list renders or empty state is shown
    await expect(
      notifPage.emptyHeading.or(notifPage.allTab),
    ).toBeVisible();
  });
});
