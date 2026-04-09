/**
 * @layer L1
 * @system notifications
 * @parameters P1, P2, P3
 * @priority P1
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { TEST_USERS } from '../../../lib/constants';
import {
  getNotificationHistoryViaApi,
} from '../../../helpers/notification.helper';

test.describe('Notification History API', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('get history returns valid response structure', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const history = await getNotificationHistoryViaApi(apiClient);
    expect(history).toHaveProperty('notifications');
    expect(history).toHaveProperty('count');
    expect(Array.isArray(history.notifications)).toBe(true);
    expect(typeof history.count).toBe('number');
  });

  test('get history without auth returns 401', async ({ apiClient }) => {
    // apiClient has no token set (no login called)
    const res = await apiClient.get('notifications/history/');
    expect(res.status).toBe(401);
  });

  test('filter by notification_type returns matching items', async ({
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const history = await getNotificationHistoryViaApi(apiClient, {
      notification_type: 'welcome',
    });

    // All items should have matching type (may be empty)
    for (const item of history.notifications) {
      expect(item.notification_type).toBe('welcome');
    }
  });

  test('user isolation — cannot see other user notifications', async ({
    apiClient,
  }) => {
    // Login as regular user
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);
    const regularHistory = await getNotificationHistoryViaApi(apiClient);

    // Login as second user
    await apiClient.login(TEST_USERS.secondUser.email, TEST_USERS.secondUser.password);
    const secondHistory = await getNotificationHistoryViaApi(apiClient);

    // IDs should not overlap
    const regularIds = new Set(regularHistory.notifications.map((n) => n.id));
    for (const item of secondHistory.notifications) {
      expect(regularIds.has(item.id)).toBe(false);
    }
  });
});
