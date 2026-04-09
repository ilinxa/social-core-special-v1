/**
 * Platform management smoke tests (members + roles).
 *
 * @layer L1
 * @system platform
 * @parameters P1, P2, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { PlatformMembersPage } from '../../../pages/platform/platform-members.page';

test.describe('Platform Management', () => {
  test('members page renders', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const membersPage = new PlatformMembersPage(page);
    await membersPage.goto();

    await expect(membersPage.heading).toBeVisible();
  });

  test('roles section visible', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const membersPage = new PlatformMembersPage(page);
    await membersPage.goto();

    await expect(membersPage.rolesHeading).toBeVisible();
  });

  test('search input is visible', async ({ platformAdminPage }) => {
    const page = platformAdminPage;
    const membersPage = new PlatformMembersPage(page);
    await membersPage.goto();

    await expect(membersPage.searchInput).toBeVisible();
  });
});
