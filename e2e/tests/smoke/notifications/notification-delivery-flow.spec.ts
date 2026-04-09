/**
 * @layer L1
 * @system notifications
 * @parameters P1, P5
 * @priority P1
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { DEFAULT_PASSWORD } from '../../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';
import {
  waitForNotificationInHistory,
  getNotificationHistoryViaApi,
} from '../../../helpers/notification.helper';
import { ApiClient } from '../../../lib/api-client';

test.describe('Notification Delivery Flow', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('registration triggers verify_email notification', async ({
    apiClient,
    dbClient,
  }) => {
    const email = generateEmail('del-reg');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    // verify_email should appear in history (mandatory, always delivered)
    const notif = await waitForNotificationInHistory(
      apiClient,
      'verify_email',
      { retries: 10, delay: 500 },
    );
    expect(notif.scope_type).toBe('user');
    expect(notif.scope_id).toBeNull();
  });

  test('login triggers new_login notification', async ({
    apiClient,
    dbClient,
  }) => {
    const email = generateEmail('del-login');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);

    // Login from a fresh client (simulates new device)
    const freshApi = new ApiClient();
    await freshApi.login(email, DEFAULT_PASSWORD);

    // new_login should appear in history
    const notif = await waitForNotificationInHistory(
      freshApi,
      'new_login',
      { retries: 10, delay: 500 },
    );
    expect(notif.scope_type).toBe('user');
  });

  test('all notification log items have required fields', async ({
    apiClient,
    dbClient,
  }) => {
    const email = generateEmail('del-fields');
    await apiClient.register(email, DEFAULT_PASSWORD, usernameFromEmail(email));
    await dbClient.verifyUserDirectly(email);
    await apiClient.login(email, DEFAULT_PASSWORD);

    const history = await getNotificationHistoryViaApi(apiClient);

    for (const item of history.notifications) {
      expect(item).toHaveProperty('id');
      expect(item).toHaveProperty('notification_type');
      expect(item).toHaveProperty('scope_type');
      expect(item).toHaveProperty('channels');
      expect(item).toHaveProperty('context');
      expect(item).toHaveProperty('status');
      expect(item).toHaveProperty('created_at');
    }
  });
});
