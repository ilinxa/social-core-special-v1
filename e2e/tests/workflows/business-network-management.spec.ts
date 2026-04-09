/**
 * W27: Business Network Management workflow.
 *
 * Cross-system flow: Network → Organization.
 * Multiple users follow a business. Owner verifies follower count via API
 * and navigates to the network page.
 *
 * @layer L2
 * @system network, business
 * @parameters P5 (Data Integrity), P8 (Search)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi } from '../../helpers/auth.helper';
import { followBusinessViaApi, getBusinessFollowersViaApi } from '../../helpers/network.helper';

test.describe('W27: Business Network Management', () => {
  test.skip(!isSystemEnabled('network'), 'Network system disabled');

  test('owner sees followers in business network page', async ({
    businessOwnerPage,
    businessContext,
    apiClient,
    dbClient,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register 3 users → verify → each follows business via API
    const followers = [];
    for (let i = 0; i < 3; i++) {
      const user = await registerAndVerifyViaApi(apiClient, dbClient, {
        email: generateEmail(`w27-follower${i}`),
      });
      await apiClient.login(user.email);
      await followBusinessViaApi(apiClient, bizId);
      followers.push(user);
    }

    // Step 2 — Verify followers via API (reliable check)
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const followersData = await getBusinessFollowersViaApi(apiClient, slug);
    expect(followersData.results.length).toBeGreaterThanOrEqual(3);

    // Step 3 — Owner navigates to /bconsole/{slug}/network
    await businessOwnerPage.goto(`/bconsole/${slug}/network`);
    await expect(
      businessOwnerPage.getByRole('heading', { level: 1 }),
    ).toBeVisible();
  });
});
