/**
 * Business context fixture — provides a pre-created business for tests.
 *
 * Extends auth fixtures with a business context (business ID, slug, etc.).
 * Business is created via API in the fixture setup, not via global-setup.
 *
 * Usage:
 * ```typescript
 * import { test, expect } from '../../fixtures/business.fixture';
 *
 * test('member list shows owner', async ({ businessOwnerPage, businessContext }) => {
 *   await businessOwnerPage.goto(`/bconsole/${businessContext.slug}/members`);
 * });
 * ```
 */

import { test as authTest } from './auth.fixture';
import { TEST_USERS } from '../lib/constants';
import { generateBusinessName, slugify } from '../lib/utils';

type BusinessContext = {
  id: string;
  slug: string;
  legalName: string;
};

type BusinessFixtures = {
  /** Pre-created business owned by the business owner test user */
  businessContext: BusinessContext;
};

export const test = authTest.extend<BusinessFixtures>({
  businessContext: async ({ apiClient, dbClient }, use) => {
    // Login as business owner
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);

    // Create a unique business for this test
    const legalName = generateBusinessName();
    const slug = slugify(legalName);
    const res = await apiClient.createBusiness({
      legal_name: legalName,
      country: 'US',
      slug,
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Failed to create business: ${body}`);
    }

    const data = (await res.json()) as { id: string; slug: string };

    // Raise max_members and enable join requests (production defaults are restrictive)
    await dbClient.setBusinessMaxMembers(data.id, 10);
    await dbClient.setBusinessOpenMemberRequest(data.id, true);

    await use({
      id: data.id,
      slug: data.slug,
      legalName,
    });
  },
});

export { expect } from '@playwright/test';
