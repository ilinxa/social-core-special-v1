/**
 * W-NOTIF-PREF: Notification Preferences Round-Trip workflow.
 *
 * Get defaults → Update → Verify → Reset → Verify defaults restored.
 *
 * @layer L2
 * @system notifications
 * @parameters P2, P3
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS } from '../../lib/constants';
import {
  getNotificationPreferenceViaApi,
  updateNotificationPreferenceViaApi,
  resetNotificationPreferenceViaApi,
} from '../../helpers/notification.helper';

test.describe('W-NOTIF-PREF: Notification Preferences Round-Trip', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('update → verify → reset → verify defaults restored', async ({
    apiClient,
  }) => {
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);
    const testType = 'new_login';

    // Step 1 — Get default preference
    const defaults = await getNotificationPreferenceViaApi(apiClient, testType);
    expect(defaults.notification_type).toBe(testType);
    expect(defaults.user_configurable).toBe(true);
    const defaultEmail = defaults.email_enabled;

    // Step 2 — Update: toggle email to opposite
    const updated = await updateNotificationPreferenceViaApi(apiClient, testType, {
      email_enabled: !defaultEmail,
    });
    expect(updated.email_enabled).toBe(!defaultEmail);

    // Step 3 — Get again to verify persistence
    const verified = await getNotificationPreferenceViaApi(apiClient, testType);
    expect(verified.email_enabled).toBe(!defaultEmail);

    // Step 4 — Reset to defaults
    await resetNotificationPreferenceViaApi(apiClient, testType);

    // Step 5 — Get again to verify defaults restored
    const restored = await getNotificationPreferenceViaApi(apiClient, testType);
    expect(restored.email_enabled).toBe(defaultEmail);
  });
});
