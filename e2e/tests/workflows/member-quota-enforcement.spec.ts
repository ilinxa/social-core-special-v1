/**
 * W15: Member Quota Enforcement workflow.
 *
 * Cross-system flow: Organization → Transaction → RBAC.
 * Tests that the member quota is enforced: fill to quota, attempt over-quota
 * (expect failure), remove a member, then successfully add again.
 *
 * @layer L2
 * @system business, transactions
 * @parameters P4 (Transaction State), P5 (Data Integrity), P10 (Limits)
 * @priority P0
 */

import { test, expect } from '../../fixtures/business.fixture';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi } from '../../helpers/auth.helper';
import {
  getBusinessMembersViaApi,
  removeBusinessMemberViaApi,
  getBaseMemberRoleId,
} from '../../helpers/business.helper';
import {
  inviteToBusinessViaApi,
  acceptTransactionViaApi,
} from '../../helpers/transaction.helper';
import { BusinessMembersPage } from '../../pages/business/business-members.page';

test.describe('W15: Member Quota Enforcement', () => {
  test('quota prevents over-limit invitation, removal allows new invitation', async ({
    apiClient,
    dbClient,
    businessOwnerPage,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Set max_members to 2 (owner counts as 1)
    await dbClient.setBusinessMaxMembers(bizId, 2);

    // Step 2 — Register user B → verify → invite → accept (fills to 2/2)
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w15-userB'),
    });
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const invB = await inviteToBusinessViaApi(apiClient, slug, bizId, userB.id);
    await apiClient.login(userB.email);
    await acceptTransactionViaApi(apiClient, invB.id as string);

    // Step 3 — Register user C → verify
    const userC = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w15-userC'),
    });

    // Step 4 — Try to create invitation for user C → expect failure (quota exceeded)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const memberRoleId = await getBaseMemberRoleId(apiClient, slug);
    const overQuotaRes = await apiClient.post('transactions/invitation/', {
      transaction_type: 'business_membership_invitation',
      target_user_id: userC.id,
      context_type: 'business',
      context_id: bizId,
      payload: { role_id: memberRoleId },
    });
    expect(overQuotaRes.status).toBeGreaterThanOrEqual(400);

    // Step 5 — Verify member count is 2 via API
    const membersCheck = await getBusinessMembersViaApi(apiClient, slug);
    expect(membersCheck.count).toBe(2);

    // Step 6 — Find member B's membership ID and remove them (search by user ID)
    const memberB = membersCheck.results.find((m) => {
      const u = (m as { user?: { id?: string } }).user;
      return u?.id === userB.id;
    });
    if (!memberB) {
      // Fallback: find the non-owner member
      const nonOwner = membersCheck.results.find(
        (m) => !(m as { is_owner?: boolean }).is_owner,
      );
      expect(nonOwner).toBeTruthy();
      await removeBusinessMemberViaApi(apiClient, slug, (nonOwner as { id: string }).id);
    } else {
      await removeBusinessMemberViaApi(apiClient, slug, (memberB as { id: string }).id);
    }

    // Step 7 — Create invitation for user C again → expect success
    const invC = await inviteToBusinessViaApi(apiClient, slug, bizId, userC.id);
    expect(invC.id).toBeTruthy();

    // Step 8 — Accept invitation → verify member count = 2 again
    await apiClient.login(userC.email);
    await acceptTransactionViaApi(apiClient, invC.id as string);

    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const updatedMembers = await getBusinessMembersViaApi(apiClient, slug);
    expect(updatedMembers.count).toBe(2);

    // Restore max_members to 10 for other tests
    await dbClient.setBusinessMaxMembers(bizId, 10);
  });
});
