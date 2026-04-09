/**
 * W6: Business Follow → Join workflow.
 *
 * Cross-system flow: Network → Transaction → Organization.
 * User follows a business, then submits a join request, owner accepts,
 * and the user gains member access.
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system network, transactions, business
 * @parameters P1 (Auth), P4 (Transaction), P5 (Data Integrity)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { followBusinessViaApi } from '../../helpers/network.helper';
import { acceptTransactionViaApi } from '../../helpers/transaction.helper';
import { BusinessProfilePage } from '../../pages/business/business-profile.page';
import { BusinessDashboardPage } from '../../pages/business/business-console.page';

test.describe('W6: Business Follow → Join', () => {
  test.skip(!isSystemEnabled('network'), 'Network system disabled');

  test('user follows business, requests to join, owner accepts, user becomes member', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register fresh user → verify
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w6-user'),
    });

    // Step 2 — Login user in new context → navigate to business public profile
    const { page: userPage, context: userCtx } = await loginInNewContext(
      browser,
      user.email,
      DEFAULT_PASSWORD,
    );
    const bizProfile = new BusinessProfilePage(userPage);
    await bizProfile.goto(slug);

    // Step 3 — Click "Follow" button → verify follow confirmed
    await expect(bizProfile.followButton).toBeVisible();
    await bizProfile.followButton.click();
    // Button should change to "Following" or "Unfollow"
    await expect(
      userPage.getByRole('button', { name: /following|unfollow/i }),
    ).toBeVisible();

    // Step 4 — Click "Request to Join" button
    await expect(bizProfile.requestToJoinButton).toBeVisible();

    // Step 5 — Click and wait for the POST request to complete before verifying via API
    await Promise.all([
      userPage.waitForResponse(
        (resp) =>
          resp.url().includes('/transactions') &&
          resp.request().method() === 'POST' &&
          resp.ok(),
      ),
      bizProfile.requestToJoinButton.click(),
    ]);
    // Verify via API that the request was created
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const txRes = await apiClient.get(
      `transactions/?context_type=business&context_id=${bizId}&status=pending&transaction_type=business_membership_request`,
    );
    const txBody = (await txRes.json()) as { results: { id: string }[] };
    expect(txBody.results.length).toBeGreaterThanOrEqual(1);

    // Step 6 — Owner accepts the request via API
    await acceptTransactionViaApi(apiClient, txBody.results[0].id);

    // Step 7 — User navigates to business dashboard → verify access
    const dashboard = new BusinessDashboardPage(userPage);
    await dashboard.goto(slug);
    await expect(dashboard.heading).toBeVisible();

    // Cleanup
    await userCtx.close();
  });
});
