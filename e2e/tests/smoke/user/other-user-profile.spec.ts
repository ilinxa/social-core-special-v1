/**
 * Other user's profile smoke tests.
 *
 * @layer L1
 * @system users
 * @parameters P1, P4, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { OtherUserProfilePage } from '../../../pages/user/other-user-profile.page';
import { TEST_USERS } from '../../../lib/constants';
import { usernameFromEmail } from '../../../lib/utils';

test.describe('Other User Profile', () => {
  test('view another user profile', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const otherProfile = new OtherUserProfilePage(page);

    // View the business owner's profile (a different user)
    const ownerUsername = usernameFromEmail(TEST_USERS.businessOwner.email);
    await otherProfile.goto(ownerUsername);

    await expect(otherProfile.heading).toBeVisible();
    await expect(otherProfile.displayName).toBeVisible();
  });

  test('non-existent user shows not found', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const otherProfile = new OtherUserProfilePage(page);
    await otherProfile.goto('nonexistent_user_e2e_xyz');

    await expect(otherProfile.notFoundMessage).toBeVisible();
  });
});
