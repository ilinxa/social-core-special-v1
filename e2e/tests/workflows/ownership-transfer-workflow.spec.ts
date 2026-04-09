/**
 * W14: Ownership Transfer workflow.
 *
 * Cross-system flow: Transaction → Organization → RBAC.
 * Uses the pre-built business. Owner invites a user, the user accepts,
 * then owner transfers ownership. New owner verifies control, old owner
 * verifies reduced permissions.
 *
 * Uses two browser contexts.
 *
 * @layer L2
 * @system transactions, business
 * @parameters P1 (Auth), P4 (Transaction), P3 (Permissions)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  inviteToBusinessViaApi,
  acceptTransactionViaApi,
  createOwnershipTransferViaApi,
} from '../../helpers/transaction.helper';
import { BusinessSettingsPage } from '../../pages/business/business-console.page';

test.describe('W14: Ownership Transfer Workflow', () => {
  test('owner transfers ownership to member, roles swap correctly', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;
    const ownerEmail = TEST_USERS.businessOwner.email;
    const ownerPassword = TEST_USERS.businessOwner.password;

    // Step 1 — Register user B → verify → invite → accept
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w14-userB'),
    });
    await apiClient.login(ownerEmail, ownerPassword);
    const inv = await inviteToBusinessViaApi(apiClient, slug, bizId, userB.id);
    await apiClient.login(userB.email);
    await acceptTransactionViaApi(apiClient, inv.id as string);

    // Step 2 — Login owner in context 1 → go to dashboard
    const { page: pageA, context: ctxA } = await loginInNewContext(
      browser,
      ownerEmail,
      ownerPassword,
    );
    await pageA.goto(`/bconsole/${slug}/dashboard`);
    await expect(pageA.getByRole('heading', { level: 1 })).toBeVisible();

    // Step 3 — Login user B in context 2
    const { page: pageB, context: ctxB } = await loginInNewContext(
      browser,
      userB.email,
      DEFAULT_PASSWORD,
    );

    // Step 4 — Owner initiates ownership transfer to B via API
    await apiClient.login(ownerEmail, ownerPassword);
    const transfer = await createOwnershipTransferViaApi(apiClient, {
      targetUserId: userB.id,
      contextType: 'business',
      contextId: bizId,
    });
    expect(transfer.id).toBeTruthy();

    // Step 5 — User B accepts transfer via API
    await apiClient.login(userB.email);
    await acceptTransactionViaApi(apiClient, transfer.id as string);

    // Step 6 — User B: navigate to settings → verify can access (is now owner)
    const settingsB = new BusinessSettingsPage(pageB);
    await settingsB.goto(slug);
    await expect(settingsB.heading).toBeVisible();
    // New owner should see the transfer ownership button (owner-only)
    await expect(settingsB.transferOwnershipButton).toBeVisible();

    // Step 7 — Owner A: navigate to settings → verify reduced permissions
    const settingsA = new BusinessSettingsPage(pageA);
    await settingsA.goto(slug);
    await expect(settingsA.heading).toBeVisible();
    // Old owner should NOT see transfer ownership button
    await expect(settingsA.transferOwnershipButton).toBeHidden();

    // Cleanup
    await ctxA.close();
    await ctxB.close();
  });
});
