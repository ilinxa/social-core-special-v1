/**
 * Business role management smoke tests.
 *
 * @layer L1
 * @system business
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { BusinessMembersPage } from '../../../pages/business/business-members.page';
import { E2E_BUSINESS } from '../../../lib/constants';

test.describe('Business Role Management', () => {
  test('roles are listed on members page', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.rolesHeading).toBeVisible();
  });

  test('create role button visible for owner', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await expect(membersPage.createRoleButton).toBeVisible();
  });

  test('create role dialog opens', async ({ businessOwnerPage }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(E2E_BUSINESS.slug);

    await membersPage.createRoleButton.click();

    // Dialog should appear with form fields
    await expect(page.getByRole('heading', { name: /create role/i })).toBeVisible();
    await expect(page.getByLabel(/name/i)).toBeVisible();
    await expect(page.getByLabel(/level/i)).toBeVisible();
  });
});
