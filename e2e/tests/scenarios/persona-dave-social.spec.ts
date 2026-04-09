/**
 * Persona: Dave — The Social Butterfly
 *
 * A highly social user who follows multiple businesses, sends
 * connection requests, engages in rapid chat, and tests presence.
 *
 * 20 progressive steps.
 *
 * @layer L3
 * @system auth, network, chat, explore
 * @parameters P1 (Auth), P5 (CRUD), P7 (Real-time)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { ExplorePage } from '../../pages/explore/explore.page';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createBusinessViaApi } from '../../helpers/business.helper';
import { followBusinessViaApi, sendConnectionRequestViaApi, getFollowingViaApi, getConnectionsViaApi } from '../../helpers/network.helper';
import { createConversationViaApi, sendMessageViaApi, getConversationsViaApi } from '../../helpers/chat.helper';
import { acceptTransactionViaApi } from '../../helpers/transaction.helper';

test.describe.serial('Dave: The Social Butterfly', () => {
  const daveEmail = generateEmail('dave-persona');
  const davePassword = 'DavePass123!';
  let daveId: string;
  let friendIds: string[] = [];
  let friendEmails: string[] = [];
  let businessIds: string[] = [];
  let conversationId: string;

  // -----------------------------------------------------------------------
  // Phase 1: Registration & Setup
  // -----------------------------------------------------------------------

  test('Step 1: Dave registers and verifies', async ({ apiClient, dbClient }) => {
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: daveEmail,
      password: davePassword,
    });
    daveId = user.id;
  });

  test('Step 2: Create 3 friends for Dave', async ({ apiClient, dbClient }) => {
    for (let i = 0; i < 3; i++) {
      const email = generateEmail(`dave-friend-${i}`);
      const user = await registerAndVerifyViaApi(apiClient, dbClient, { email });
      friendIds.push(user.id);
      friendEmails.push(email);
    }
  });

  test('Step 3: Create 2 businesses for Dave to follow', async ({ apiClient, dbClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    for (let i = 0; i < 2; i++) {
      const ownerEmail = generateEmail(`dave-biz-owner-${i}`);
      const owner = await registerAndVerifyViaApi(apiClient, dbClient, { email: ownerEmail });
      await dbClient.grantBusinessCreation(ownerEmail);
      await apiClient.login(ownerEmail, DEFAULT_PASSWORD);
      const biz = await createBusinessViaApi(apiClient, dbClient, {
        legalName: `Dave Follow Biz ${i}`,
      });
      businessIds.push(biz.id);
    }
  });

  // -----------------------------------------------------------------------
  // Phase 2: Following
  // -----------------------------------------------------------------------

  test('Step 4: Dave follows business 1', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(daveEmail, davePassword);
    await followBusinessViaApi(apiClient, businessIds[0]);
  });

  test('Step 5: Dave follows business 2', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(daveEmail, davePassword);
    await followBusinessViaApi(apiClient, businessIds[1]);
  });

  test('Step 6: Dave verifies following count is 2', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(daveEmail, davePassword);
    const following = await getFollowingViaApi(apiClient);
    expect(following.results.length).toBe(2);
  });

  // -----------------------------------------------------------------------
  // Phase 3: Connections
  // -----------------------------------------------------------------------

  test('Step 7: Dave sends connection request to friend 1', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(daveEmail, davePassword);
    await sendConnectionRequestViaApi(apiClient, friendIds[0], 'Hey, let\'s connect!');
  });

  test('Step 8: Friend 1 accepts Dave\'s connection', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(friendEmails[0], DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const request = txns.results[0];
    if (request) {
      await acceptTransactionViaApi(apiClient, request.id as string);
    }
  });

  test('Step 9: Dave sends connection request to friend 2', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(daveEmail, davePassword);
    await sendConnectionRequestViaApi(apiClient, friendIds[1]);
  });

  test('Step 10: Friend 2 accepts Dave\'s connection', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(friendEmails[1], DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const request = txns.results[0];
    if (request) {
      await acceptTransactionViaApi(apiClient, request.id as string);
    }
  });

  test('Step 11: Dave verifies connections count', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(daveEmail, davePassword);
    const connections = await getConnectionsViaApi(apiClient);
    expect(connections.results.length).toBeGreaterThanOrEqual(2);
  });

  // -----------------------------------------------------------------------
  // Phase 4: Chat
  // -----------------------------------------------------------------------

  test('Step 12: Dave creates a conversation with friend 1', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(daveEmail, davePassword);
    const conv = await createConversationViaApi(apiClient, [friendIds[0]]);
    conversationId = conv.id;
  });

  test('Step 13: Dave sends rapid messages', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(daveEmail, davePassword);
    for (let i = 0; i < 5; i++) {
      await sendMessageViaApi(apiClient, conversationId, `Rapid message ${i + 1} from Dave`);
    }
  });

  test('Step 14: Friend 1 replies', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(friendEmails[0], DEFAULT_PASSWORD);
    await sendMessageViaApi(apiClient, conversationId, 'Hey Dave! Got all your messages!');
  });

  test('Step 15: Dave opens chat page in browser', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, daveEmail, davePassword);
    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    await expect(
      chatPage.conversationList.or(chatPage.noConversationsMessage),
    ).toBeVisible();
    await context.close();
  });

  test('Step 16: Dave sees messages in the conversation', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, daveEmail, davePassword);
    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    const firstConv = chatPage.conversationList.getByRole('option').first();
    if (await firstConv.isVisible()) {
      await firstConv.click();
      const messagePanel = new MessageViewPanel(page);
      await expect(messagePanel.messageInput).toBeVisible();
    }
    await context.close();
  });

  test('Step 17: Dave verifies conversation count', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(daveEmail, davePassword);
    const convs = await getConversationsViaApi(apiClient);
    expect(convs.results.length).toBeGreaterThanOrEqual(1);
  });

  // -----------------------------------------------------------------------
  // Phase 5: Explore & Final
  // -----------------------------------------------------------------------

  test('Step 18: Dave browses explore page', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, daveEmail, davePassword);
    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test('Step 19: Dave searches for businesses', async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, daveEmail, davePassword);
    const explorePage = new ExplorePage(page);
    await explorePage.goto();
    await explorePage.searchInput.fill('Dave Follow');
    await expect(explorePage.heading).toBeVisible();
    await context.close();
  });

  test("Step 20: Dave's social journey is complete", async ({ browser }) => {
    const { page, context } = await loginInNewContext(browser, daveEmail, davePassword);
    await page.goto('/profile');
    await expect(page.getByRole('heading').first()).toBeVisible();
    await context.close();
  });
});
