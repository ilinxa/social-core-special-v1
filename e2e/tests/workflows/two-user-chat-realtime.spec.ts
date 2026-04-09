/**
 * W8: Two-User Chat Real-time workflow.
 *
 * Verifies real-time WebSocket chat: two users with open chat pages,
 * one sends a message, the other sees it appear in real-time without refresh.
 *
 * Uses two browser contexts with the Daphne ASGI backend for WebSocket support.
 *
 * @layer L2
 * @system chat, auth
 * @parameters P1 (Auth), P7 (Real-time), P5 (Data Integrity)
 * @priority P0
 */

import { test, expect } from '../../fixtures/base.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createConversationViaApi,
  sendMessageViaApi,
  acceptChatRequestViaApi,
} from '../../helpers/chat.helper';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';

test.describe('W8: Two-User Chat Real-time', () => {
  test.skip(!isSystemEnabled('chat'), 'Chat system disabled');

  test('two users exchange messages in real-time via WebSocket', async ({
    browser,
    apiClient,
    dbClient,
  }) => {
    // Step 1 — Register user A and user B via API → verify both
    const userA = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w8-userA'),
    });
    const userB = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w8-userB'),
    });

    // Step 2 — Create DM conversation via API (as user A, participant: user B)
    await apiClient.login(userA.email);
    const conversation = await createConversationViaApi(apiClient, [userB.id]);

    // Step 3 — User A sends a message via API (so conversation has content)
    await sendMessageViaApi(apiClient, conversation.id, 'Hello from user A!');

    // Step 4 — User B accepts the chat request (unconnected users → PENDING request)
    await apiClient.login(userB.email);
    await acceptChatRequestViaApi(apiClient, conversation.id);

    // Step 5 — Login user A in context 1 → navigate to /chat
    const { page: pageA, context: ctxA } = await loginInNewContext(
      browser,
      userA.email,
      DEFAULT_PASSWORD,
    );
    const chatPageA = new ChatPage(pageA);
    await chatPageA.goto();

    // Step 6 — Login user B in context 2 → navigate to /chat
    const { page: pageB, context: ctxB } = await loginInNewContext(
      browser,
      userB.email,
      DEFAULT_PASSWORD,
    );
    const chatPageB = new ChatPage(pageB);
    await chatPageB.goto();

    // Step 7 — User A: click on first conversation in list
    const convItemA = chatPageA.conversationList.getByRole('option').first();
    await expect(convItemA).toBeVisible({ timeout: 15000 });
    await convItemA.click();

    // Step 8 — User A: verify message visible
    await expect(pageA.getByText('Hello from user A!')).toBeVisible({ timeout: 10000 });

    // Step 9 — User B: click first conversation in the list
    const convItemB = chatPageB.conversationList.getByRole('option').first();
    await expect(convItemB).toBeVisible({ timeout: 15000 });
    await convItemB.click();

    // Step 10 — User B: verify user A's message visible
    await expect(pageB.getByText('Hello from user A!')).toBeVisible({ timeout: 10000 });

    // Step 11 — User B: type reply → send (Enter key — ComposeBar handles Enter)
    const messagePanelB = new MessageViewPanel(pageB);
    await expect(messagePanelB.messageInput).toBeVisible({ timeout: 10000 });
    await messagePanelB.messageInput.fill('Reply from user B!');
    await messagePanelB.messageInput.press('Enter');

    // Step 12 — User B: verify own message appears
    await expect(pageB.getByText('Reply from user B!')).toBeVisible({ timeout: 10000 });

    // Step 13 — User A: verify reply appears in real-time (without refresh)
    await expect(pageA.getByText('Reply from user B!')).toBeVisible({ timeout: 15000 });

    // Cleanup
    await ctxA.close();
    await ctxB.close();
  });
});
