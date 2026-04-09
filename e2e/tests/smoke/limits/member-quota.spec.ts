/**
 * Member quota limit smoke tests.
 *
 * Verifies the quota bar renders on the members dashboard and
 * that the quota-full state is visually communicated.
 *
 * @layer L1
 * @system business, limits
 * @parameters P1, P5, P10
 * @priority P2
 */

import { test, expect } from '../../../fixtures/business.fixture';
import { BusinessMembersPage } from '../../../pages/business/business-members.page';

test.describe('Member Quota', () => {
  test('members page renders quota indicator', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(businessContext.slug);

    await expect(membersPage.heading).toBeVisible();
    // QuotaBar renders either a progressbar or "X / Y" text
    await expect(membersPage.quotaBar).toBeVisible();
  });

  test('quota shows member count with format X / Y', async ({ businessOwnerPage, businessContext }) => {
    const page = businessOwnerPage;
    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(businessContext.slug);

    // Business fixture sets max_members=10, owner is 1 member → "1 / 10" format
    await expect(page.getByText(/\d+\s*\/\s*\d+/).first()).toBeVisible();
  });

  test('quota at full capacity shows 1 / 1 when max is 1', async ({ businessOwnerPage, businessContext, dbClient }) => {
    const page = businessOwnerPage;

    // Lower the max_members to 1 (owner is already 1 member → full)
    await dbClient.setBusinessMaxMembers(businessContext.id, 1);

    const membersPage = new BusinessMembersPage(page);
    await membersPage.goto(businessContext.slug);

    await expect(membersPage.heading).toBeVisible();
    // At full quota, should show "1 / 1" (member count equals max)
    await expect(page.getByText('1 / 1')).toBeVisible();
  });
});
