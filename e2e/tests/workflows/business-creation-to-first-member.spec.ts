/**
 * W2: Business Creation → First Member workflow.
 *
 * Cross-system flow: Auth → Organization → Transaction → RBAC.
 * A user creates a business, invites another user, the invitee accepts,
 * and the owner verifies the new member appears in the member list.
 *
 * Uses two browser contexts (owner + invitee).
 *
 * @layer L2
 * @system auth, business, transactions
 * @parameters P1 (Auth), P2 (Navigation), P4 (Transaction State), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail, generateBusinessName } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createBusinessViaApi, getBusinessMembersViaApi } from '../../helpers/business.helper';
import { createInvitationViaApi, acceptTransactionViaApi } from '../../helpers/transaction.helper';
import { BusinessDashboardPage } from '../../pages/business/business-console.page';
import { BusinessMembersPage } from '../../pages/business/business-members.page';

test.describe('W2: Business Creation → First Member', () => {
  test.skip(!isSystemEnabled('organization'), 'Organization system disabled');

  test('owner creates business, invites user, invitee accepts, member appears', async ({
    browser,
    apiClient,
    dbClient,
  }) => {
    // Step 1 — Register owner (user A) via API → verify email
    const ownerApi = apiClient;
    const owner = await registerAndVerifyViaApi(ownerApi, dbClient, {
      email: generateEmail('w2-owner'),
    });

    // Step 2 — Grant business creation permission
    await dbClient.grantBusinessCreation(owner.email);

    // Step 3 — Re-login to pick up updated permissions
    await ownerApi.login(owner.email);

    // Step 4 — Create business via API
    const bizName = generateBusinessName('W2');
    const business = await createBusinessViaApi(ownerApi, dbClient, { legalName: bizName });

    // Step 5 — Login owner in browser context 1, navigate to dashboard
    const { page: ownerPage, context: ownerCtx } = await loginInNewContext(
      browser,
      owner.email,
      DEFAULT_PASSWORD,
    );
    const dashboardPage = new BusinessDashboardPage(ownerPage);
    await dashboardPage.goto(business.slug);
    await expect(dashboardPage.heading).toBeVisible();

    // Step 6 — Register invitee (user B) via API → verify email
    const inviteeApi = apiClient;
    const invitee = await registerAndVerifyViaApi(inviteeApi, dbClient, {
      email: generateEmail('w2-invitee'),
    });

    // Step 7 — Switch back to owner's API context and create invitation for invitee
    await ownerApi.login(owner.email);
    const invitation = await createInvitationViaApi(ownerApi, {
      targetUserId: invitee.id,
      contextType: 'business',
      contextId: business.id,
    });
    expect(invitation.id).toBeTruthy();

    // Step 8 — Login invitee in browser context 2
    const { page: inviteePage, context: inviteeCtx } = await loginInNewContext(
      browser,
      invitee.email,
      DEFAULT_PASSWORD,
    );

    // Step 9 — Invitee navigates to activity page → sees pending invitation
    await inviteePage.goto('/activity');
    await expect(
      inviteePage.getByText(/invitation/i).first(),
    ).toBeVisible();

    // Step 10 — Accept invitation via API (as invitee)
    await inviteeApi.login(invitee.email);
    await acceptTransactionViaApi(inviteeApi, invitation.id as string);

    // Step 11 — Owner navigates to members page
    const membersPage = new BusinessMembersPage(ownerPage);
    await membersPage.goto(business.slug);
    await expect(membersPage.heading).toBeVisible();

    // Step 12 — Verify member count reflects both owner + new member
    // The members list should show the invitee's username
    await expect(ownerPage.getByText(new RegExp(invitee.username, 'i'))).toBeVisible();

    // Step 13 — Invitee verifies access to business dashboard
    await inviteePage.goto(`/bconsole/${business.slug}/dashboard`);
    await expect(
      inviteePage.getByRole('heading', { level: 1 }),
    ).toBeVisible();

    // Cleanup contexts
    await ownerCtx.close();
    await inviteeCtx.close();
  });
});
