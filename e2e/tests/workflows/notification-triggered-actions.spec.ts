/**
 * W12: Notification Triggered Actions workflow.
 *
 * Registration → verify_email log; Login → new_login log;
 * Transaction → scoped notification log.
 *
 * @layer L2
 * @system notifications, auth
 * @parameters P1, P5
 * @priority P0
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import {
  getNotificationHistoryViaApi,
  waitForNotificationInHistory,
} from '../../helpers/notification.helper';
import { ApiClient } from '../../lib/api-client';

test.describe('W12: Notification Triggered Actions', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('actions trigger scoped notifications in history', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();
    const email = generateEmail('notif-trig');
    const username = usernameFromEmail(email);

    // Step 1 — Register triggers verify_email notification
    await apiClient.register(email, DEFAULT_PASSWORD, username);
    await dbClient.verifyUserDirectly(email);

    // Re-login to get fresh token after verification
    await apiClient.login(email, DEFAULT_PASSWORD);

    // Step 2 — Check history for verify_email with scope_type=user
    const verifyNotif = await waitForNotificationInHistory(
      apiClient,
      'verify_email',
      { retries: 10, delay: 500 },
    );
    expect(verifyNotif.scope_type).toBe('user');
    expect(verifyNotif.scope_id).toBeNull();

    // Step 3 — Login from "new device" triggers new_login
    const freshApi = new ApiClient();
    await freshApi.login(email, DEFAULT_PASSWORD);

    const loginNotif = await waitForNotificationInHistory(
      freshApi,
      'new_login',
      { retries: 10, delay: 500 },
    );
    expect(loginNotif.scope_type).toBe('user');

    // Step 4 — Business transaction triggers scoped notification
    // Create a business, then invite the second user
    await dbClient.grantBusinessCreation(email);
    await freshApi.login(email, DEFAULT_PASSWORD);
    const bizRes = await freshApi.post('business/', {
      legal_name: `Notif Biz ${ts}`,
      country: 'US',
      slug: `notif-biz-${ts}`,
    });

    if (bizRes.ok) {
      const biz = (await bizRes.json()) as { id: string };

      // Get second user ID for invitation
      const secondApi = new ApiClient();
      await secondApi.login(TEST_USERS.secondUser.email, TEST_USERS.secondUser.password);
      const secondProfile = await secondApi.get('users/profile/');
      if (secondProfile.ok) {
        const secondUser = (await secondProfile.json()) as { id: string };

        // Create invitation transaction
        await freshApi.createInvitation({
          transaction_type: 'member_invitation',
          target_user_id: secondUser.id,
          context_type: 'business',
          context_id: biz.id,
        });

        // Check second user's history for business-scoped notification
        const inviteNotif = await waitForNotificationInHistory(
          secondApi,
          'transaction_invitation_received',
          { retries: 10, delay: 500, scope_type: 'business', scope_id: biz.id },
        );
        expect(inviteNotif.scope_type).toBe('business');
        expect(inviteNotif.scope_id).toBe(biz.id);
      }
    }
  });
});
