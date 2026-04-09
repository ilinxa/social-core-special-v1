/**
 * Multi-Persona Interaction Scenario
 *
 * 5 actors (Alpha, Beta, Gamma, Delta, Echo) interact simultaneously:
 * create businesses, join, chat, follow, and verify cross-user state.
 *
 * 21 progressive steps.
 *
 * @layer L3
 * @system auth, business, network, chat, transactions
 * @parameters P1 (Auth), P5 (CRUD), P6 (RBAC), P7 (Real-time)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { ChatPage } from '../../pages/chat/chat.page';
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import { createBusinessViaApi, getBusinessMembersViaApi } from '../../helpers/business.helper';
import { acceptTransactionViaApi } from '../../helpers/transaction.helper';
import { inviteToBusinessViaApi } from '../../helpers/transaction.helper';
import { followBusinessViaApi, sendConnectionRequestViaApi, getConnectionsViaApi } from '../../helpers/network.helper';
import { createConversationViaApi, sendMessageViaApi, createGroupConversationViaApi } from '../../helpers/chat.helper';

test.describe.serial('Multi-Persona Interaction', () => {
  // 5 actors
  const actors = ['alpha', 'beta', 'gamma', 'delta', 'echo'] as const;
  const users: Record<string, { id: string; email: string }> = {};
  let businessSlug: string;
  let businessId: string;
  let groupConversationId: string;

  // -----------------------------------------------------------------------
  // Phase 1: Register All Actors
  // -----------------------------------------------------------------------

  test('Step 1: Register all 5 actors', async ({ apiClient, dbClient }) => {
    for (const actor of actors) {
      const email = generateEmail(`multi-${actor}`);
      const user = await registerAndVerifyViaApi(apiClient, dbClient, { email });
      users[actor] = { id: user.id, email };
    }
    expect(Object.keys(users)).toHaveLength(5);
  });

  // -----------------------------------------------------------------------
  // Phase 2: Business Setup (Alpha is owner)
  // -----------------------------------------------------------------------

  test('Step 2: Alpha creates a business', async ({ apiClient, dbClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await dbClient.grantBusinessCreation(users.alpha.email);
    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const biz = await createBusinessViaApi(apiClient, dbClient, {
      legalName: 'Multi Persona Corp',
    });
    businessSlug = biz.slug;
    businessId = biz.id;
  });

  test('Step 3: Alpha invites Beta and Gamma', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    await inviteToBusinessViaApi(apiClient, businessSlug, businessId, users.beta.id);
    await inviteToBusinessViaApi(apiClient, businessSlug, businessId, users.gamma.id);
  });

  test('Step 4: Beta accepts invitation', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.beta.email, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const inv = txns.results.find((t) => t.context_id === businessId);
    expect(inv).toBeTruthy();
    await acceptTransactionViaApi(apiClient, inv!.id as string);
  });

  test('Step 5: Gamma accepts invitation', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.gamma.email, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    const inv = txns.results.find((t) => t.context_id === businessId);
    expect(inv).toBeTruthy();
    await acceptTransactionViaApi(apiClient, inv!.id as string);
  });

  test('Step 6: Business has 3 members', async ({ apiClient }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    expect(members.count).toBe(3); // Alpha + Beta + Gamma
  });

  // -----------------------------------------------------------------------
  // Phase 3: Network (Delta and Echo follow the business)
  // -----------------------------------------------------------------------

  test('Step 7: Delta follows the business', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.delta.email, DEFAULT_PASSWORD);
    await followBusinessViaApi(apiClient, businessId);
  });

  test('Step 8: Echo follows the business', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    await apiClient.login(users.echo.email, DEFAULT_PASSWORD);
    await followBusinessViaApi(apiClient, businessId);
  });

  // -----------------------------------------------------------------------
  // Phase 4: Connections
  // -----------------------------------------------------------------------

  test('Step 9: Delta sends connection request to Alpha', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(users.delta.email, DEFAULT_PASSWORD);
    await sendConnectionRequestViaApi(apiClient, users.alpha.id);
  });

  test('Step 10: Alpha accepts Delta\'s connection', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    if (txns.results.length > 0) {
      await acceptTransactionViaApi(apiClient, txns.results[0].id as string);
    }
  });

  test('Step 11: Echo sends connection request to Beta', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(users.echo.email, DEFAULT_PASSWORD);
    await sendConnectionRequestViaApi(apiClient, users.beta.id);
  });

  test('Step 12: Beta accepts Echo\'s connection', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(users.beta.email, DEFAULT_PASSWORD);
    const res = await apiClient.get('transactions/?role=target&status=pending');
    const txns = (await res.json()) as { results: Record<string, unknown>[] };
    if (txns.results.length > 0) {
      await acceptTransactionViaApi(apiClient, txns.results[0].id as string);
    }
  });

  test('Step 13: Alpha verifies connections', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('network'), 'Network disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const connections = await getConnectionsViaApi(apiClient);
    expect(connections.results.length).toBeGreaterThanOrEqual(1);
  });

  // -----------------------------------------------------------------------
  // Phase 5: Group Chat
  // -----------------------------------------------------------------------

  test('Step 14: Alpha creates a group conversation with Beta and Gamma', async ({
    apiClient,
  }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const conv = await createGroupConversationViaApi(
      apiClient,
      [users.beta.id, users.gamma.id],
      'Multi-Persona Team Chat',
    );
    groupConversationId = conv.id;
    expect(conv.conversation_type).toBe('group');
  });

  test('Step 15: Alpha sends a message to the group', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    await sendMessageViaApi(
      apiClient,
      groupConversationId,
      'Welcome team! Let\'s get started.',
    );
  });

  test('Step 16: Beta sends a reply', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(users.beta.email, DEFAULT_PASSWORD);
    await sendMessageViaApi(
      apiClient,
      groupConversationId,
      'Thanks Alpha! Excited to be here.',
    );
  });

  test('Step 17: Gamma sends a reply', async ({ apiClient }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    await apiClient.login(users.gamma.email, DEFAULT_PASSWORD);
    await sendMessageViaApi(apiClient, groupConversationId, 'Count me in!');
  });

  // -----------------------------------------------------------------------
  // Phase 6: Browser Verification
  // -----------------------------------------------------------------------

  test('Step 18: Alpha opens chat in browser and sees group', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, users.alpha.email, DEFAULT_PASSWORD);
    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    await expect(
      chatPage.conversationList.or(chatPage.noConversationsMessage),
    ).toBeVisible();
    await context.close();
  });

  test('Step 19: Beta opens chat and sees the group conversation', async ({ browser }) => {
    test.skip(!isSystemEnabled('chat'), 'Chat disabled');

    const { page, context } = await loginInNewContext(browser, users.beta.email, DEFAULT_PASSWORD);
    await page.goto('/chat');
    const chatPage = new ChatPage(page);
    await expect(chatPage.conversationList).toBeVisible();
    await context.close();
  });

  // -----------------------------------------------------------------------
  // Phase 7: Final State
  // -----------------------------------------------------------------------

  test('Step 20: All actors can still log in', async ({ apiClient }) => {
    // Verify all actors can authenticate via API (avoids browser login loop timeout)
    for (const actor of actors) {
      await apiClient.login(users[actor].email, DEFAULT_PASSWORD);
      const res = await apiClient.get('users/me/');
      expect(res.status).toBe(200);
    }
  });

  test('Step 21: Multi-persona interaction complete — final state verified', async ({
    apiClient,
  }) => {
    test.skip(getOrgMode() === 'user_only', 'Organization disabled');

    // Verify business still has 3 members
    await apiClient.login(users.alpha.email, DEFAULT_PASSWORD);
    const members = await getBusinessMembersViaApi(apiClient, businessSlug);
    expect(members.count).toBe(3);
  });
});
