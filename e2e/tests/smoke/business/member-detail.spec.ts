/**
 * Business member detail smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P5, P7
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessMembersPage } from '../../../pages/business/business-members.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Member Detail', () => {
  test('members page shows at least the owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.heading).toBeVisible();
    // At least one member card (the owner) should exist
    await expect(page.getByText(/owner/i).first()).toBeVisible();
  });
});
