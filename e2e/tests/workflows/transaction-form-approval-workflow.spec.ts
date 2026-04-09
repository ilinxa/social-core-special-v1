/**
 * W5: Transaction Approval workflow.
 *
 * Cross-system flow: Transaction → Organization → RBAC.
 * User submits a join request, owner reviews and approves,
 * user becomes an active member.
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system transactions, business, forms
 * @parameters P4 (Transaction State), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createJoinRequestViaApi,
  acceptTransactionViaApi,
} from '../../helpers/transaction.helper';
import { BusinessMembersPage } from '../../pages/business/business-members.page';
import { BusinessDashboardPage } from '../../pages/business/business-console.page';

test.describe('W5: Transaction Approval Workflow', () => {
  test.skip(!isSystemEnabled('forms'), 'Forms system disabled');

  test('owner approves join request, user becomes active member', async ({
    browser,
    apiClient,
    dbClient,
    businessOwnerPage,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register fresh user → verify
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w5-user'),
    });

    // Step 2 — Submit join request via API (as the user)
    await apiClient.login(user.email);
    const request = await createJoinRequestViaApi(apiClient, {
      contextType: 'business',
      contextId: bizId,
    });
    expect(request.id).toBeTruthy();

    // Step 3 — Owner page → navigate to transactions/requests → see pending
    await businessOwnerPage.goto(`/bconsole/${slug}/transactions/requests`);
    await expect(
      businessOwnerPage.getByText(/pending/i).first(),
    ).toBeVisible();

    // Step 4 — Accept the request via API (as owner)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    await acceptTransactionViaApi(apiClient, request.id as string);

    // Step 5 — Verify new member via API (reliable check)
    const { getBusinessMembersViaApi } = await import('../../helpers/business.helper');
    const members = await getBusinessMembersViaApi(apiClient, slug);
    const newMemberInList = members.results.find((m) => {
      const u = (m as { user?: { email?: string }; user_email?: string }).user;
      return u?.email === user.email || (m as { user_email?: string }).user_email === user.email;
    });
    expect(newMemberInList).toBeTruthy();

    // Navigate to members page → verify heading
    const membersPage = new BusinessMembersPage(businessOwnerPage);
    await membersPage.goto(slug);
    await expect(membersPage.heading).toBeVisible();

    // Step 6 — New user verifies access to bconsole dashboard
    const { page: userPage, context: userCtx } = await loginInNewContext(
      browser,
      user.email,
      DEFAULT_PASSWORD,
    );
    const dashboardPage = new BusinessDashboardPage(userPage);
    await dashboardPage.goto(slug);
    await expect(dashboardPage.heading).toBeVisible();

    // Cleanup
    await userCtx.close();
  });
});
