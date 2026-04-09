/**
 * Business member actions smoke tests (suspend/ban/reactivate).
 *
 * @layer L1
 * @system business
 * @parameters P2, P5, P7
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessMembersPage } from '../../../pages/business/business-members.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Member Actions', () => {
  test('owner sees the member list', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.heading).toBeVisible();
  });
});
