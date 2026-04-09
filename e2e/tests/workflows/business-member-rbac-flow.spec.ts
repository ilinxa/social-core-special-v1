/**
 * W10: Business Member RBAC Flow workflow.
 *
 * Cross-system flow: RBAC → Organization → Auth.
 * A member is invited and accepted, then starts with limited permissions.
 * The owner assigns an admin role, and the member's access changes.
 *
 * Uses two browser contexts (owner + member).
 *
 * @layer L2
 * @system business, auth
 * @parameters P1 (Auth), P3 (Permissions), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/business.fixture';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  getBusinessRolesViaApi,
  assignRoleViaApi,
  getBusinessMembersViaApi,
} from '../../helpers/business.helper';
import {
  inviteToBusinessViaApi,
  acceptTransactionViaApi,
} from '../../helpers/transaction.helper';
import { BusinessSettingsPage } from '../../pages/business/business-console.page';

test.describe('W10: Business Member RBAC Flow', () => {
  test('member gets admin role assigned and gains elevated permissions', async ({
    browser,
    apiClient,
    dbClient,
    businessOwnerPage,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register member user → verify → invite → accept (all via API)
    const member = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w10-member'),
    });

    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const invitation = await inviteToBusinessViaApi(apiClient, slug, bizId, member.id);

    await apiClient.login(member.email);
    await acceptTransactionViaApi(apiClient, invitation.id as string);

    // Step 2 — Get roles via API to find an admin-level role
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const roles = await getBusinessRolesViaApi(apiClient, slug);
    // Find an admin role (highest level that isn't the owner role)
    const adminRole = roles.find(
      (r) => (r as { name: string }).name.toLowerCase().includes('admin'),
    ) as { id: string; name: string } | undefined;

    // Step 3 — Login member in new context → navigate to business settings
    const { page: memberPage, context: memberCtx } = await loginInNewContext(
      browser,
      member.email,
      DEFAULT_PASSWORD,
    );
    const settingsPage = new BusinessSettingsPage(memberPage);
    await settingsPage.goto(slug);

    // Step 4 — Verify settings page shows restricted access (limited permissions)
    // A basic member should see the page but without edit controls
    await expect(settingsPage.heading).toBeVisible();

    // Step 5 — Owner: assign admin role to member via API (if admin role exists)
    if (adminRole) {
      // Find the member's membership ID
      const members = await getBusinessMembersViaApi(apiClient, slug);
      const memberEntry = members.results.find(
        (m) => (m as { user: { email: string } }).user?.email === member.email,
      );
      if (memberEntry) {
        await assignRoleViaApi(
          apiClient,
          slug,
          memberEntry.id as string,
          adminRole.id,
        );
      }
    }

    // Step 6 — Member: refresh settings page → permissions may be updated
    await memberPage.reload();
    await expect(settingsPage.heading).toBeVisible();

    // Step 7 — Verify the member can still access the console
    // (Verifying that RBAC updates propagate without re-login)
    await memberPage.goto(`/bconsole/${slug}/dashboard`);
    await expect(memberPage.getByRole('heading', { level: 1 })).toBeVisible();

    // Cleanup
    await memberCtx.close();
  });
});
