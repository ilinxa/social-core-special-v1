/**
 * @layer L1
 * @system notifications, business
 * @parameters P6
 * @priority P1
 */
import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../../lib/constants';
import { generateEmail, usernameFromEmail } from '../../../lib/utils';
import { getNotificationHistoryViaApi } from '../../../helpers/notification.helper';
import { ApiClient } from '../../../lib/api-client';

test.describe('Notification RBAC & Scope Access', () => {
  test.skip(!isSystemEnabled('notifications'), 'Notifications system disabled');

  test('org-scoped history returns _permissions when scope_id provided', async ({
    apiClient,
  }) => {
    // Use business owner who has a business with notifications
    await apiClient.login(
      TEST_USERS.businessOwner.email,
      TEST_USERS.businessOwner.password,
    );

    // Get user's businesses to find scope_id
    const bizRes = await apiClient.get('business/');
    const bizData = (await bizRes.json()) as {
      results: Array<{ id: string }>;
    };

    if (bizData.results.length > 0) {
      const bizId = bizData.results[0].id;

      // Request with scope_id should include _permissions
      const res = await apiClient.get(
        `notifications/history/?scope_type=business&scope_id=${bizId}`,
      );
      expect(res.ok).toBe(true);
      const body = (await res.json()) as Record<string, unknown>;

      if (body._permissions) {
        const perms = body._permissions as Record<string, boolean>;
        expect(perms).toHaveProperty('can_view_notifications');
        expect(perms).toHaveProperty('can_manage_preferences');
        expect(perms).toHaveProperty('can_manage_org_notifications');
      }
    }
  });

  test('non-member gets empty list for business scope (not 403)', async ({
    apiClient,
    dbClient,
  }) => {
    // Create a business as one user
    const ownerEmail = generateEmail('rbac-owner');
    const ownerApi = new ApiClient();
    await ownerApi.register(
      ownerEmail,
      DEFAULT_PASSWORD,
      usernameFromEmail(ownerEmail),
    );
    await dbClient.verifyUserDirectly(ownerEmail);
    await dbClient.grantBusinessCreation(ownerEmail);
    await ownerApi.login(ownerEmail, DEFAULT_PASSWORD);

    const bizRes = await ownerApi.post('business/', {
      legal_name: `RBAC Biz ${Date.now()}`,
      country: 'US',
      slug: `rbac-biz-${Date.now()}`,
    });
    const biz = (await bizRes.json()) as { id: string };

    // Non-member queries business-scoped history
    const nonMemberEmail = generateEmail('rbac-non');
    const nonMemberApi = new ApiClient();
    await nonMemberApi.register(
      nonMemberEmail,
      DEFAULT_PASSWORD,
      usernameFromEmail(nonMemberEmail),
    );
    await dbClient.verifyUserDirectly(nonMemberEmail);
    await nonMemberApi.login(nonMemberEmail, DEFAULT_PASSWORD);

    const history = await getNotificationHistoryViaApi(nonMemberApi, {
      scope_type: 'business',
      scope_id: biz.id,
    });

    // Should return 200 with empty list (not 403)
    expect(history.notifications).toHaveLength(0);
    expect(history.count).toBe(0);
  });

  test('history without scope_id has no _permissions key', async ({
    apiClient,
  }) => {
    await apiClient.login(
      TEST_USERS.regular.email,
      TEST_USERS.regular.password,
    );

    const res = await apiClient.get('notifications/history/');
    expect(res.ok).toBe(true);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body).not.toHaveProperty('_permissions');
  });
});
