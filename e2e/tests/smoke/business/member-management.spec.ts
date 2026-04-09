/**
 * Business member management smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P2, P4, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessMembersPage } from '../../../pages/business/business-members.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Member Management', () => {
  test('members page renders with member list', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.heading).toBeVisible();
  });

  test('search input is visible', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.searchInput).toBeVisible();
  });

  test('create role button is visible for owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.createRoleButton).toBeVisible();
  });

  test('roles section is visible', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.rolesHeading).toBeVisible();
  });
});
