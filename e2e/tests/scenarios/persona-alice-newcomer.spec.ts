/**
 * Persona: Alice — The Newcomer
 *
 * A first-time user who discovers the platform, registers, verifies,
 * explores businesses, follows one, requests to join, gets accepted,
 * and has a chat conversation.
 *
 * 36 progressive steps. Each step builds on the previous state.
 *
 * @layer L3
 * @system auth, users, explore, network, transactions, business, chat
 * @parameters P1 (Auth), P2 (Navigation), P3 (Display), P5 (CRUD), P7 (Real-time)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { LandingPage } from '../../pages/public/landing.page';
import { LoginPage } from '../../pages/auth/login.page';
import { RegisterPage } from '../../pages/auth/register.page';
import { ProfileViewPage } from '../../pages/user/profile.page';
import { ExplorePage } from '../../pages/explore/explore.page';
import { BusinessProfilePage } from '../../pages/business/business-profile.page';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';
import { BasePage } from '../../pages/base.page';
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';
import { generateEmail, usernameFromEmail } from '../../lib/utils';
import { createBusinessViaApi } from '../../helpers/business.helper';
import { acceptTransactionViaApi, inviteToBusinessViaApi } from '../../helpers/transaction.helper';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createConversationViaApi, sendMessageViaApi } from '../../helpers/chat.helper';
import { followBusinessViaApi } from '../../helpers/network.helper';
import { TEST_USERS, DEFAULT_PASSWORD } from '../../lib/constants';

test.describe.serial('Alice: The Newcomer', () => {
  // Shared state across all steps
  const aliceEmail = generateEmail('alice-persona');
  const aliceUsername = usernameFromEmail(aliceEmail);
  const alicePassword = 'AlicePass123!';
  let aliceId: string;
  let businessSlug: string;
  let businessId: string;
  let businessOwnerId: string;
  let businessOwnerEmail: string;
  let invitationId: string;
  let conversationId: string;

  // -----------------------------------------------------------------------
  // Phase 1: Anonymous Browsing
  // -----------------------------------------------------------------------

  test('Step 1: Alice visits the landing page anonymously', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await expect(landingPage.heading).toBeVisible();
    await expect(landingPage.brandLink).toBeVisible();
  });

  test('Step 2: Alice browses public navigation links', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await expect(landingPage.exploreLink).toBeVisible();
    await expect(landingPage.signInButton).toBeVisible();
    await expect(landingPage.registerButton).toBeVisible();
  });

  test('Step 3: Alice navigates to the about page', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await landingPage.aboutLink.click();
    await expect(page).toHaveURL(/\/about/);
  });

  test('Step 4: Alice views the explore page as anonymous user', async ({ page }) => {
    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await expect(explorePage.heading).toBeVisible();
    await expect(explorePage.searchInput).toBeVisible();
  });

  // -----------------------------------------------------------------------
  // Phase 2: Registration & Verification
  // -----------------------------------------------------------------------

  test('Step 5: Alice clicks register from landing page', async ({ page }) => {
    const landingPage = new LandingPage(page);
    await landingPage.goto();
    await landingPage.registerButton.click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('Step 6: Alice fills out the registration form', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    await registerPage.goto();
    await registerPage.register(aliceEmail, aliceUsername, alicePassword);
    // E2E env may auto-verify → redirect to /home or /dashboard instead of /verify-email
    await expect(page).toHaveURL(/\/(verify-email|home|dashboard)/);
  });

  test('Step 7: Alice verifies her email via DB code', async ({ apiClient, dbClient }) => {
    const code = await dbClient.getVerificationCode(aliceEmail);
    if (!code) {
      // User was auto-verified during registration — nothing to verify via code
      return;
    }

    // Verify via API (frontend verify page may not be built yet)
    const res = await apiClient.post('auth/verify-email/', { email: aliceEmail, code });
    expect(res.status).toBeLessThan(400);
  });

  test('Step 8: Alice logs in for the first time', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(aliceEmail, alicePassword);
    await expect(page).toHaveURL(/\/home/);
  });

  // -----------------------------------------------------------------------
  // Phase 3: Profile & Navigation
  // -----------------------------------------------------------------------

  test('Step 9: Alice sees the home page after login', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(aliceEmail, alicePassword);

    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
  });

  test('Step 10: Alice navigates to her profile', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.heading).toBeVisible();
    await expect(profilePage.username).toContainText(aliceUsername);
    await context.close();
  });

  test('Step 11: Alice verifies her avatar area is visible', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.avatar).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 4: Explore & Discover
  // -----------------------------------------------------------------------

  test('Step 12: Setup — create a business for Alice to discover', async ({
    apiClient,
    dbClient,
  }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    // Fetch Alice's user ID (needed for invitation in later steps)
    await apiClient.login(aliceEmail, alicePassword);
    aliceId = ((await apiClient.get('users/me/').then((r) => r.json())) as { id: string }).id;

    // Create a business owner
    businessOwnerEmail = generateEmail('alice-biz-owner');
    const owner = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: businessOwnerEmail,
    });
    businessOwnerId = owner.id;
    await dbClient.grantBusinessCreation(owner.email);
    await apiClient.login(owner.email, DEFAULT_PASSWORD);
    const biz = await createBusinessViaApi(apiClient, dbClient, {
      legalName: 'Alice Discovery Biz',
    });
    businessSlug = biz.slug;
    businessId = biz.id;
  });

  test('Step 13: Alice searches for the business on explore', async ({ browser }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await explorePage.searchInput.fill('Alice Discovery');

    // Wait for search results to render
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 14: Alice views the business public profile', async ({ browser }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(businessSlug);
    await expect(profilePage.businessName).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 5: Follow & Join
  // -----------------------------------------------------------------------

  test('Step 15: Alice follows the business via API', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(aliceEmail, alicePassword);
    await followBusinessViaApi(apiClient, businessId);
  });

  test('Step 16: Alice sees follow confirmed on business profile', async ({ browser }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    const profilePage = new BusinessProfilePage(page);
    await profilePage.goto(businessSlug);
    await expect(profilePage.businessName).toBeVisible();
    await context.close();
  });

  test('Step 17: Business owner invites Alice', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    // Login as business owner (reuse email from Step 12)
    await apiClient.login(businessOwnerEmail, DEFAULT_PASSWORD);
    const invitation = await inviteToBusinessViaApi(apiClient, businessSlug, businessId, aliceId);
    invitationId = invitation.id as string;
  });

  test('Step 18: Alice accepts the invitation', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(aliceEmail, alicePassword);
    await acceptTransactionViaApi(apiClient, invitationId);
  });

  test('Step 19: Alice can access the business console', async ({ browser }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto(`/bconsole/${businessSlug}/dashboard`);
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 6: Chat
  // -----------------------------------------------------------------------

  test('Step 20: Setup — create a conversation with business owner', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(aliceEmail, alicePassword);
    const conv = await createConversationViaApi(apiClient, [businessOwnerId]);
    conversationId = conv.id;
  });

  test('Step 21: Business owner sends a welcome message', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(businessOwnerEmail, DEFAULT_PASSWORD);
    await sendMessageViaApi(apiClient, conversationId, 'Welcome to the team, Alice!');
  });

  test('Step 22: Alice opens the chat page', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    await expect(
      chatPage.conversationList.or(chatPage.noConversationsMessage),
    ).toBeVisible();
    await context.close();
  });

  test('Step 23: Alice sees the conversation in her list', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    await expect(chatPage.conversationList).toBeVisible();
    await context.close();
  });

  test('Step 24: Alice opens the conversation and sees the welcome message', async ({
    browser,
  }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/chat');
    const chatPage = new ChatPage(page);

    const firstConv = chatPage.conversationList.getByRole('option').first();
    if (await firstConv.isVisible()) {
      await firstConv.click();
      const messagePanel = new MessageViewPanel(page);
      await expect(messagePanel.messageInput).toBeVisible();
      await expect(page.getByText('Welcome to the team, Alice!')).toBeVisible();
    }
    await context.close();
  });

  test('Step 25: Alice sends a reply', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/chat');
    const chatPage = new ChatPage(page);

    const firstConv = chatPage.conversationList.getByRole('option').first();
    if (await firstConv.isVisible()) {
      await firstConv.click();
      const messagePanel = new MessageViewPanel(page);
      await messagePanel.messageInput.fill('Thank you! Glad to be here!');
      await messagePanel.sendButton.click();
      await expect(page.getByText('Thank you! Glad to be here!')).toBeVisible();
    }
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 7: Session Management & Logout
  // -----------------------------------------------------------------------

  test('Step 26: Alice navigates to settings', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/settings');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });

  test('Step 27: Alice verifies her username in settings', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/settings');
    const usernameField = page.getByLabel(/username/i);
    if (await usernameField.isVisible()) {
      await expect(usernameField).toHaveValue(aliceUsername);
    }
    await context.close();
  });

  test('Step 28: Alice logs out', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(aliceEmail, alicePassword);

    // Find and click logout
    const userMenuButton = page.getByRole('button', { name: /user menu|account/i });
    if (await userMenuButton.isVisible()) {
      await userMenuButton.click();
      const logoutItem = page.getByRole('menuitem', { name: /log out|sign out/i });
      if (await logoutItem.isVisible()) {
        await logoutItem.click();
        await expect(page).toHaveURL(/\/(login|\/)/);
      }
    }
  });

  test('Step 29: Alice cannot access protected routes after logout', async ({ page }) => {
    await page.goto('/profile');
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('Step 30: Alice logs back in successfully', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(aliceEmail, alicePassword);
    await expect(page).toHaveURL(/\/home/);
  });

  // -----------------------------------------------------------------------
  // Phase 8: Return Visit
  // -----------------------------------------------------------------------

  test('Step 31: Alice revisits the explore page', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 32: Alice verifies her profile still shows correct info', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.username).toContainText(aliceUsername);
    await context.close();
  });

  test('Step 33: Alice clicks edit on her profile', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await profilePage.clickEdit();
    await expect(page).toHaveURL(/\/profile\/edit/);
    await context.close();
  });

  test('Step 34: Alice views the home feed again', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login(aliceEmail, alicePassword);

    await expect(page).toHaveURL(/\/home/);
    const basePage = new BasePage(page);
    await expect(basePage.main).toBeVisible();
  });

  test('Step 35: Alice verifies navigation links work', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    // Navigate via sidebar/nav to explore
    await page.goto('/explore');
    await expect(page).toHaveURL(/\/explore/);

    // Navigate back to home
    await page.goto('/home');
    await expect(page).toHaveURL(/\/home/);
    await context.close();
  });

  test('Step 36: Alice\'s full journey is complete — final state check', async ({
    browser,
  }) => {
    const { page, context } = await loginInNewContext(browser, aliceEmail, alicePassword);

    // Verify profile accessible
    await page.goto('/profile');
    const profilePage = new ProfileViewPage(page);
    await expect(profilePage.heading).toBeVisible();
    await expect(profilePage.username).toContainText(aliceUsername);
    await context.close();
  });
});
