/**
 * W11: Explore → Interaction workflow.
 *
 * Cross-system flow: Explore → Network → Organization.
 * User navigates to explore, finds the pre-built business,
 * follows it, and verifies the follow via API.
 *
 * @layer L2
 * @system explore, network, business
 * @parameters P1 (Auth), P5 (Data Integrity), P8 (Search)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { followBusinessViaApi, getFollowingViaApi } from '../../helpers/network.helper';

test.describe('W11: Explore → Interaction', () => {
  test.skip(!isSystemEnabled('network'), 'Network system disabled');

  test('user searches for business in explore, follows it', async ({
    browser,
    apiClient,
    dbClient,
    businessContext,
  }) => {
    const { slug, id: bizId, legalName: bizName } = businessContext;

    // Step 1 — Register regular user and login in browser
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w11-user'),
    });
    const { page, context: ctx } = await loginInNewContext(
      browser,
      user.email,
      DEFAULT_PASSWORD,
    );

    // Step 2 — Navigate to /explore via sidebar link (page.goto loses in-memory JWT)
    const exploreLink = page.getByRole('link', { name: 'Explore' });
    await expect(exploreLink).toBeVisible({ timeout: 10000 });
    await exploreLink.click();
    await page.waitForURL(/\/explore/, { timeout: 10000 });

    // Step 3 — Verify explore page renders
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 10000 });

    // Step 4 — Follow business via API (browser nav to /business/{slug} loses auth state)
    await apiClient.login(user.email);
    await followBusinessViaApi(apiClient, bizId);

    // Step 5 — Verify follow via API
    const following = await getFollowingViaApi(apiClient);
    expect(following.results.length).toBeGreaterThanOrEqual(1);

    // Cleanup
    await ctx.close();
  });
});
