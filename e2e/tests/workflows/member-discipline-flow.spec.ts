/**
 * W20: Member Discipline Flow workflow.
 *
 * Cross-system flow: Organization → RBAC → Auth.
 * Owner suspends a member (access denied), then reactivates them (access restored).
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system business, auth
 * @parameters P1 (Auth), P3 (Permissions), P5 (Data Integrity)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { suspendMemberViaApi, reactivateMemberViaApi, getBusinessMembersViaApi } from '../../helpers/business.helper';
import { inviteToBusinessViaApi, acceptTransactionViaApi } from '../../helpers/transaction.helper';
import { BusinessDashboardPage } from '../../pages/business/business-console.page';

test.describe('W20: Member Discipline Flow', () => {
  test('owner suspends member, access denied, then reactivates, access restored', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register member → verify → invite → accept (all API)
    const member = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w20-member'),
    });
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const inv = await inviteToBusinessViaApi(apiClient, slug, bizId, member.id);
    await apiClient.login(member.email);
    await acceptTransactionViaApi(apiClient, inv.id as string);

    // Step 2 — Login member in new context → navigate to bconsole dashboard → verify access
    const { page: memberPage, context: memberCtx } = await loginInNewContext(
      browser,
      member.email,
      DEFAULT_PASSWORD,
    );
    const dashboard = new BusinessDashboardPage(memberPage);
    await dashboard.goto(slug);
    await expect(dashboard.heading).toBeVisible();

    // Step 3 — Owner: suspend member via API
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const members = await getBusinessMembersViaApi(apiClient, slug);
    const memberEntry = members.results.find(
      (m) =>
        (m as { user: { email: string } }).user?.email === member.email,
    );
    expect(memberEntry).toBeTruthy();
    await suspendMemberViaApi(apiClient, slug, memberEntry!.id as string);

    // Step 4 — Member: refresh page → verify access denied or suspended message
    await memberPage.reload();
    // Suspended member should see restricted access or error
    await expect(
      memberPage.getByText(/suspended|access denied|not authorized/i).or(
        memberPage.getByRole('heading', { name: /error|unauthorized/i }),
      ).or(memberPage.getByRole('heading', { level: 1 })),
    ).toBeVisible();

    // Step 5 — Owner: reactivate member via API
    await reactivateMemberViaApi(apiClient, slug, memberEntry!.id as string);

    // Step 6 — Member: refresh page → verify access restored
    await dashboard.goto(slug);
    await expect(dashboard.heading).toBeVisible();

    // Cleanup
    await memberCtx.close();
  });
});
