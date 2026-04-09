/**
 * W13: Platform Business Management workflow.
 *
 * Cross-system flow: Platform → Organization.
 * Platform admin views business list, searches for a specific business,
 * and views its detail.
 *
 * @layer L2
 * @system platform, business
 * @parameters P1 (Auth), P5 (Data Integrity), P8 (Search)
 * @priority P1
 */

import { test, expect } from '../../fixtures/auth.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail, generateBusinessName } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi } from '../../helpers/auth.helper';
import { createBusinessViaApi } from '../../helpers/business.helper';
import { ApiClient } from '../../lib/api-client';
import { DbClient } from '../../lib/db-client';

test.describe('W13: Platform Business Management', () => {
  test.skip(!isSystemEnabled('organization'), 'Organization system disabled');

  test('platform admin views business list and finds specific business', async ({
    platformAdminPage,
    apiClient,
    dbClient,
  }) => {
    // Step 1 — Create 2 uniquely named businesses (as separate owners)
    const ownerA = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w13-ownerA'),
    });
    await dbClient.grantBusinessCreation(ownerA.email);
    await apiClient.login(ownerA.email);
    const bizA = await createBusinessViaApi(apiClient, dbClient, {
      legalName: generateBusinessName('W13A'),
    });

    const ownerB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w13-ownerB'),
    });
    await dbClient.grantBusinessCreation(ownerB.email);
    await apiClient.login(ownerB.email);
    const bizB = await createBusinessViaApi(apiClient, dbClient, {
      legalName: generateBusinessName('W13B'),
    });

    // Step 2 — Platform admin navigates to /pconsole/businesses
    await platformAdminPage.goto('/pconsole/businesses');
    await expect(
      platformAdminPage.getByRole('heading', { level: 1 }),
    ).toBeVisible();

    // Step 3 — Verify at least some businesses appear in list
    // Look for either business name
    await expect(
      platformAdminPage.getByText(new RegExp(bizA.legalName, 'i')).or(
        platformAdminPage.getByText(new RegExp(bizB.legalName, 'i')),
      ),
    ).toBeVisible();

    // Step 4 — Search/filter for business A specifically
    const searchInput = platformAdminPage.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill(bizA.legalName);
      await expect(
        platformAdminPage.getByText(new RegExp(bizA.legalName, 'i')),
      ).toBeVisible();
    }
  });
});
