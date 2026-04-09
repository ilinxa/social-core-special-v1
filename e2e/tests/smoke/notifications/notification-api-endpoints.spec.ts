/**
 * @layer L1
 * @system notifications
 * @parameters P1, P2, P7
 * @priority P1
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { TEST_USERS } from '../../../lib/constants';
import {
  getNotificationScopesViaApi,
  getConfigurableTypesViaApi,
  getNotificationPreferenceViaApi,
  updateNotificationPreferenceViaApi,
} from '../../../helpers/notification.helper';

test.describe('Notification API Endpoints', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('scopes endpoint returns valid structure', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const scopes = await getNotificationScopesViaApi(apiClient);
    expect(scopes).toHaveProperty('scopes');
    expect(scopes).toHaveProperty('count');
    expect(Array.isArray(scopes.scopes)).toBe(true);
    expect(typeof scopes.count).toBe('number');
  });

  test('types endpoint returns configurable types only', async ({
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const types = await getConfigurableTypesViaApi(apiClient);
    expect(types).toHaveProperty('types');
    expect(types).toHaveProperty('count');
    expect(Array.isArray(types.types)).toBe(true);

    // Non-configurable types should NOT be in the list
    const typeNames = types.types.map((t) => t.name);
    expect(typeNames).not.toContain('verify_email');
    expect(typeNames).not.toContain('welcome');
    expect(typeNames).not.toContain('password_reset');
    expect(typeNames).not.toContain('password_changed');
    expect(typeNames).not.toContain('suspicious_activity');

    // Configurable types should be present
    expect(typeNames).toContain('new_login');
    expect(typeNames).toContain('newsletter');
  });

  test('single preference detail returns all fields', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const pref = await getNotificationPreferenceViaApi(apiClient, 'new_login');
    expect(pref.notification_type).toBe('new_login');
    expect(pref.display_name).toBeDefined();
    expect(pref.description).toBeDefined();
    expect(pref.category).toBeDefined();
    expect(typeof pref.user_configurable).toBe('boolean');
    expect(typeof pref.email_enabled).toBe('boolean');
    expect(typeof pref.push_enabled).toBe('boolean');
    expect(typeof pref.sms_enabled).toBe('boolean');
  });

  test('update non-configurable type is rejected', async ({ apiClient }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    const res = await apiClient.patch('notifications/preferences/verify_email/', {
      email_enabled: false,
    });
    expect(res.status).toBe(400);
  });
});
