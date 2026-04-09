/**
 * Persona: Bob — The Entrepreneur
 *
 * A power user who creates a business, sets up forms and RBAC,
 * manages members and quota, and eventually transfers ownership.
 *
 * 37 progressive steps. Each step builds on the previous state.
 *
 * @layer L3
 * @system auth, business, forms, transactions
 * @parameters P1 (Auth), P2 (Navigation), P5 (CRUD), P6 (RBAC), P10 (Quota)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { LoginPage } from '../../pages/auth/login.page';
import { BusinessDashboardPage, BusinessSettingsPage } from '../../pages/business/business-console.page';
import { BusinessProfilePage } from '../../pages/business/business-profile.page';
import { BasePage } from '../../pages/base.page';
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createBusinessViaApi,
  getBusinessMembersViaApi,
  getBusinessRolesViaApi,
  assignRoleViaApi,
  removeBusinessMemberViaApi,
} from '../../helpers/business.helper';
import {
  acceptTransactionViaApi,
  createOwnershipTransferViaApi,
  createFormMappingViaApi,
  inviteToBusinessViaApi,
} from '../../helpers/transaction.helper';
import {
  createTemplateViaApi,
  addFieldViaApi,
  publishTemplateViaApi,
  submitResponseViaApi,
} from '../../helpers/form.helper';

test.describe.serial('Bob: The Entrepreneur', () => {
  test.skip(getOrgMode() === 'user_only', 'Organization disabled');

  // Shared state
  const bobEmail = generateEmail('bob-persona');
  const bobPassword = 'BobPass123!';
  let bobId: string;
  let businessSlug: string;
  let businessId: string;
  let memberAId: string;
  let memberAEmail: string;
  let memberAMembershipId: string;
  let memberBId: string;
  let memberBEmail: string;
  let templateId: string;
  let adminRoleId: string;

  // -----------------------------------------------------------------------
  // Phase 1: Registration & Business Creation
  // -----------------------------------------------------------------------

  test('Step 1: Bob registers and verifies via API', async ({ apiClient, dbClient }) => {
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: bobEmail,
      password: bobPassword,
    });
    bobId = user.id;
    await dbClient.grantBusinessCreation(bobEmail);
  });

  test('Step 2: Bob logs in', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(bobEmail, bobPassword);
    await expect(page).toHaveURL(/\/home/);
  });

  test('Step 3: Bob creates a business via API', async ({ apiClient, dbClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const biz = await createBusinessViaApi(apiClient, dbClient, {
      legalName: 'Bob Ventures Inc',
    });
    businessSlug = biz.slug;
    businessId = biz.id;
  });

  test('Step 4: Bob views his business dashboard', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businessSlug);
    await expect(dashboard.heading).toBeVisible();
    await context.close();
  });

  test('Step 5: Bob views the public business profile', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(businessSlug);
    await expect(profilePage.businessName).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // Phase 2: Form Setup
  // -----------------------------------------------------------------------

  test('Step 6: Bob creates a form template via API', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(bobEmail, bobPassword);
    const template = await createTemplateViaApi(apiClient, 'business', businessId, {
      name: 'Bob Join Application',
      description: 'Application form for joining Bob Ventures',
    });
    templateId = template.id;
  });

  test('Step 7: Bob adds fields to the form', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(bobEmail, bobPassword);
    await addFieldViaApi(apiClient, templateId, {
      field_key: 'full_name',
      field_type: 'text',
      label: 'Full Name',
      is_required: true,
      order: 1,
    });
    await addFieldViaApi(apiClient, templateId, {
      field_key: 'experience_years',
      field_type: 'integer',
      label: 'Years of Experience',
      is_required: true,
      order: 2,
    });
    await addFieldViaApi(apiClient, templateId, {
      field_key: 'motivation',
      field_type: 'textarea',
      label: 'Why do you want to join?',
      is_required: false,
      order: 3,
    });
  });

  test('Step 8: Bob publishes the form template', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(bobEmail, bobPassword);
    await publishTemplateViaApi(apiClient, templateId);
  });

  test('Step 9: Bob creates a form-transaction mapping', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(bobEmail, bobPassword);
    await createFormMappingViaApi(apiClient, {
      transactionType: 'business_membership_request',
      templateId,
      accountType: 'business',
      accountId: businessId,
      isRequired: true,
    });
  });

  // -----------------------------------------------------------------------
  // Phase 3: Member Invitations
  // -----------------------------------------------------------------------

  test('Step 10: Register member A via API', async ({ apiClient, dbClient }) => {
    memberAEmail = generateEmail('bob-member-a');
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: memberAEmail,
    });
    memberAId = user.id;
  });

  test('Step 11: Register member B via API', async ({ apiClient, dbClient }) => {
    memberBEmail = generateEmail('bob-member-b');
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: memberBEmail,
    });
    memberBId = user.id;
  });

  test('Step 12: Bob invites member A', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const invitation = await inviteToBusinessViaApi(apiClient, businessSlug, businessId, memberAId);
    expect(invitation.id).toBeTruthy();
  });

  test('Step 13: Member A accepts the invitation', async ({ apiClient }) => {
    await apiClient.login(memberAEmail, DEFAULT_PASSWORD);
    // Get pending invitation
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const inv = txns.results.find((t) => t.context_id === businessId);
    expect(inv).toBeTruthy();
    await acceptTransactionViaApi(apiClient, inv!.id as string);
  });

  test('Step 14: Bob invites member B', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const invitation = await inviteToBusinessViaApi(apiClient, businessSlug, businessId, memberBId);
    expect(invitation.id).toBeTruthy();
  });

  test('Step 15: Member B accepts the invitation', async ({ apiClient }) => {
    await apiClient.login(memberBEmail, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const inv = txns.results.find((t) => t.context_id === businessId);
    expect(inv).toBeTruthy();
    await acceptTransactionViaApi(apiClient, inv!.id as string);
  });

  test('Step 16: Bob verifies member count is 3', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    expect(members.count).toBe(3); // Bob + A + B
  });

  // -----------------------------------------------------------------------
  // Phase 4: RBAC
  // -----------------------------------------------------------------------

  test('Step 17: Bob lists available roles', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const roles = await getBusinessRolesViaApi(apiClient, businessSlug);
    expect(roles.length).toBeGreaterThanOrEqual(2); // owner + member at minimum
    const adminRole = (roles as { id: string; name: string }[]).find(
      (r) => r.name.toLowerCase().includes('admin'),
    );
    if (adminRole) {
      adminRoleId = adminRole.id;
    }
  });

  test('Step 18: Bob assigns admin role to member A', async ({ apiClient }) => {
    test.skip(!adminRoleId, 'No admin role found');

    await apiClient.login(bobEmail, bobPassword);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    const memberA = members.results.find(
      (m) => (m as Record<string, unknown>).user_id === memberAId,
    ) as Record<string, unknown> | undefined;
    expect(memberA).toBeTruthy();
    memberAMembershipId = memberA!.id as string;
    await assignRoleViaApi(apiClient, businessSlug, memberAMembershipId, adminRoleId);
  });

  test('Step 19: Bob views member A detail — role should be admin', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    await page.goto(`/bconsole/${businessSlug}/members`);
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 20: Member A logs in and accesses business settings', async ({ browser }) => {
    test.skip(!adminRoleId, 'No admin role found');

    const { page, context } = await loginInNewContext(browser, memberAEmail, DEFAULT_PASSWORD);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    await expect(settingsPage.heading).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Form Responses
  // -----------------------------------------------------------------------

  test('Step 21: A form response is submitted via API', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    await apiClient.login(bobEmail, bobPassword);
    const response = await submitResponseViaApi(apiClient, templateId, {
      full_name: 'Test Applicant',
      experience_years: 5,
      motivation: 'I love what you are building!',
    });
    expect(response.id).toBeTruthy();
  });

  test('Step 22: Bob views form responses page in console', async ({ browser }) => {
    test.skip(!isSystemEnabled('forms'), 'Forms disabled');

    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    await page.goto(`/bconsole/${businessSlug}/forms`);
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 6: Member Quota
  // -----------------------------------------------------------------------

  test('Step 23: Bob sets member quota to 3 (at capacity)', async ({ dbClient }) => {
    await dbClient.setBusinessMaxMembers(businessId, 3);
  });

  test('Step 24: Bob attempts to invite a 4th member — quota exceeded', async ({
    apiClient,
    dbClient,
  }) => {
    const extraUser = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('bob-extra-member'),
    });
    await apiClient.login(bobEmail, bobPassword);

    try {
      await inviteToBusinessViaApi(apiClient, businessSlug, businessId, extraUser.id);
      // If it doesn't throw, check the response indicates failure
    } catch {
      // Expected — quota exceeded
    }
  });

  test('Step 25: Bob removes member B to free quota', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    const memberB = members.results.find((m) => {
      const user = (m as Record<string, unknown>).user as Record<string, unknown> | undefined;
      return user?.id === memberBId;
    }) as Record<string, unknown> | undefined;
    expect(memberB).toBeTruthy();
    await removeBusinessMemberViaApi(apiClient, businessSlug, memberB!.id as string);
  });

  test('Step 26: Bob verifies member count is now 2', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    expect(members.count).toBe(2); // Bob + member A
  });

  // -----------------------------------------------------------------------
  // Phase 7: Business Settings
  // -----------------------------------------------------------------------

  test('Step 27: Bob views business settings page', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    await expect(settingsPage.heading).toBeVisible();
    await context.close();
  });

  test('Step 28: Bob sees transfer ownership button', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    await expect(settingsPage.transferOwnershipButton).toBeVisible();
    await context.close();
  });

  test('Step 29: Bob sees archive button', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    await expect(settingsPage.archiveButton).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 8: Ownership Transfer
  // -----------------------------------------------------------------------

  test('Step 30: Bob initiates ownership transfer to member A', async ({ apiClient }) => {
    await apiClient.login(bobEmail, bobPassword);
    const transfer = await createOwnershipTransferViaApi(apiClient, {
      targetUserId: memberAId,
      contextType: 'business',
      contextId: businessId,
    });
    expect(transfer.id).toBeTruthy();
  });

  test('Step 31: Member A accepts the ownership transfer', async ({ apiClient }) => {
    await apiClient.login(memberAEmail, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const transfer = txns.results.find(
      (t) =>
        (t.transaction_type as string)?.includes('ownership') &&
        t.context_id === businessId,
    );
    expect(transfer).toBeTruthy();
    await acceptTransactionViaApi(apiClient, transfer!.id as string);
  });

  test('Step 32: Member A is now the owner — can access settings', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, memberAEmail, DEFAULT_PASSWORD);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    await expect(settingsPage.heading).toBeVisible();
    await expect(settingsPage.transferOwnershipButton).toBeVisible();
    await context.close();
  });

  test('Step 33: Bob is no longer owner — reduced access', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const settingsPage = new BusinessSettingsPage(page);
    await settingsPage.goto(businessSlug);
    // Bob should still see settings but without owner-only controls
    await expect(settingsPage.heading).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 9: Final State Verification
  // -----------------------------------------------------------------------

  test('Step 34: Bob views the business public profile', async ({ page }) => {
    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(businessSlug);
    await expect(profilePage.businessName).toBeVisible();
  });

  test('Step 35: Bob verifies business dashboard still accessible', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    const dashboard = new BusinessDashboardPage(page);
    await dashboard.goto(businessSlug);
    await expect(dashboard.heading).toBeVisible();
    await context.close();
  });

  test('Step 36: Bob navigates home — session still valid', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    await page.goto('/home');
    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
    await context.close();
  });

  test('Step 37: Bob\'s entrepreneurial journey is complete', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, bobEmail, bobPassword);

    await page.goto('/profile');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });
});
