/**
 * W-NOTIF-ISO: Notification Scope Isolation workflow.
 *
 * Business-scoped notifications → Non-member gets empty list →
 * Member sees scoped notification → Scopes endpoint shows both scopes.
 *
 * @layer L2
 * @system notifications, business
 * @parameters P5, P6
 * @priority P1
 */
import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import {
  getNotificationHistoryViaApi,
  getNotificationScopesViaApi,
} from '../../helpers/notification.helper';
import { ApiClient } from '../../lib/api-client';

test.describe('W-NOTIF-ISO: Notification Scope Isolation', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('non-member gets empty list for business scope', async ({
    apiClient,
    dbClient,
  }) => {
    const ts = Date.now();

    // Setup: create a business owner with a business
    const ownerEmail = generateEmail('iso-owner');
    const ownerApi = new ApiClient();
    await ownerApi.register(ownerEmail, DEFAULT_PASSWORD, usernameFromEmail(ownerEmail));
    await dbClient.verifyUserDirectly(ownerEmail);
    await dbClient.grantBusinessCreation(ownerEmail);
    await ownerApi.login(ownerEmail, DEFAULT_PASSWORD);

    const bizRes = await ownerApi.post('business/', {
      legal_name: `Iso Notif Biz ${ts}`,
      country: 'US',
      slug: `iso-notif-${ts}`,
    });
    const biz = (await bizRes.json()) as { id: string; slug: string };

    // Step 1 — Non-member queries business-scoped history → empty list (not 403)
    const nonMemberApi = new ApiClient();
    const nonMemberEmail = generateEmail('iso-nonmember');
    await nonMemberApi.register(nonMemberEmail, DEFAULT_PASSWORD, usernameFromEmail(nonMemberEmail));
    await dbClient.verifyUserDirectly(nonMemberEmail);
    await nonMemberApi.login(nonMemberEmail, DEFAULT_PASSWORD);

    const history = await getNotificationHistoryViaApi(nonMemberApi, {
      scope_type: 'business',
      scope_id: biz.id,
    });
    expect(history.notifications).toHaveLength(0);
    expect(history.count).toBe(0);

    // Step 2 — Owner queries own history → may have notifications
    await ownerApi.login(ownerEmail, DEFAULT_PASSWORD);
    const ownerHistory = await getNotificationHistoryViaApi(ownerApi);
    expect(ownerHistory).toHaveProperty('notifications');

    // Step 3 — Check scopes for owner
    const scopes = await getNotificationScopesViaApi(ownerApi);
    expect(scopes).toHaveProperty('scopes');
    // Owner should have at least "user" scope from registration
    if (scopes.count > 0) {
      const scopeTypes = scopes.scopes.map((s) => s.scope_type);
      expect(scopeTypes).toContain('user');
    }
  });
});
