/**
 * W3: Member Invitation Full Cycle workflow.
 *
 * Cross-system flow: Transaction → Organization → RBAC.
 * Uses the pre-built business owner + context. Owner invites a fresh user,
 * the invitee sees the pending invitation, accepts it, and both sides verify
 * the membership is active.
 *
 * Uses two browser contexts (owner pre-auth + invitee fresh).
 *
 * @layer L2
 * @system transactions, business
 * @parameters P1 (Auth), P4 (Transaction State), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/business.fixture';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { getBusinessMembersViaApi } from '../../helpers/business.helper';
import {
  inviteToBusinessViaApi,
  acceptTransactionViaApi,
} from '../../helpers/transaction.helper';
import { BusinessMembersPage } from '../../pages/business/business-members.page';
import { BusinessDashboardPage } from '../../pages/business/business-console.page';
import { ActivityPage } from '../../pages/transactions/transactions.page';
import { TEST_USERS } from '../../lib/constants';

test.describe('W3: Member Invitation Full Cycle', () => {
  test('owner invites user, invitee sees and accepts, both verify membership', async ({
    browser,
    apiClient,
    dbClient,
    businessOwnerPage,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register fresh invitee via API → verify email → get user ID
    const invitee = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w3-invitee'),
    });

    // Step 2 — Create invitation via API as business owner
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const invitation = await inviteToBusinessViaApi(apiClient, slug, bizId, invitee.id);
    expect(invitation.id).toBeTruthy();

    // Step 3 — Owner navigates to business invitations list
    await businessOwnerPage.goto(`/bconsole/${slug}/transactions`);
    await expect(
      businessOwnerPage.getByRole('heading', { level: 1 }),
    ).toBeVisible();

    // Step 4 — Verify invitation appears
    await businessOwnerPage.goto(`/bconsole/${slug}/transactions/invitations`);
    // The pending invitation should be in the list
    await expect(
      businessOwnerPage.getByText(/pending/i).first(),
    ).toBeVisible();

    // Step 5 — Login invitee in new context → navigate to activity page
    const { page: inviteePage, context: inviteeCtx } = await loginInNewContext(
      browser,
      invitee.email,
      DEFAULT_PASSWORD,
    );
    const activityPage = new ActivityPage(inviteePage);
    await activityPage.goto();
    await expect(activityPage.heading).toBeVisible();

    // Step 6 — Verify incoming invitation visible
    await expect(inviteePage.getByText(/invitation/i).first()).toBeVisible();

    // Step 7 — Accept invitation via API (as invitee)
    await apiClient.login(invitee.email);
    await acceptTransactionViaApi(apiClient, invitation.id as string);

    // Step 8 — Verify membership via API (reliable check)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const members = await getBusinessMembersViaApi(apiClient, slug);
    const inviteeInList = members.results.find((m) => {
      const user = (m as { user?: { email?: string }; user_email?: string }).user;
      return user?.email === invitee.email || (m as { user_email?: string }).user_email === invitee.email;
    });
    expect(inviteeInList).toBeTruthy();

    // Step 9 — Owner navigates to members page → verify heading loads
    const membersPage = new BusinessMembersPage(businessOwnerPage);
    await membersPage.goto(slug);
    await expect(membersPage.heading).toBeVisible();

    // Step 10 — Invitee navigates to business dashboard → verify access
    const inviteeDashboard = new BusinessDashboardPage(inviteePage);
    await inviteeDashboard.goto(slug);
    await expect(inviteeDashboard.heading).toBeVisible();

    // Cleanup
    await inviteeCtx.close();
  });
});
