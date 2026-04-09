/**
 * W16: Entity Chat Business Context workflow.
 *
 * Cross-system flow: Chat → Organization → RBAC.
 * Business owner creates a conversation with an external user and sends
 * a message. The external user verifies the message is received.
 *
 * Uses API + browser verification.
 *
 * @layer L2
 * @system chat, business
 * @parameters P1 (Auth), P7 (Real-time), P5 (Data Integrity)
 * @priority P1
 */

import { test, expect } from '../../fixtures/business.fixture';
import { isSystemEnabled } from '../../lib/feature-gates';
import { generateEmail } from '../../lib/utils';
import { DEFAULT_PASSWORD, TEST_USERS } from '../../lib/constants';
import { registerAndVerifyViaApi, loginInNewContext } from '../../helpers/auth.helper';
import {
  createConversationViaApi,
  sendMessageViaApi,
  acceptChatRequestViaApi,
  getMessagesViaApi,
} from '../../helpers/chat.helper';
import { ChatPage, MessageViewPanel } from '../../pages/chat/chat.page';

test.describe('W16: Entity Chat Business Context', () => {
  test.skip(!isSystemEnabled('chat'), 'Chat system disabled');

  test('business owner sends message, external user receives it', async ({
    browser,
    apiClient,
    dbClient,
    businessOwnerPage,
    businessContext,
  }) => {
    const { slug, id: bizId } = businessContext;

    // Step 1 — Register external user → verify
    const externalUser = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('w16-ext'),
    });

    // Step 2 — Create conversation in GLOBAL scope (so external user can see it)
    // Business-scoped conversations only appear in bconsole chat, not /chat
    await apiClient.login(TEST_USERS.businessOwner.email, TEST_USERS.businessOwner.password);
    const conversation = await createConversationViaApi(apiClient, [externalUser.id]);

    // Step 3 — Send message as business owner via API
    await sendMessageViaApi(apiClient, conversation.id, 'Message from business owner');

    // Step 4 — External user accepts chat request (unconnected users → PENDING)
    await apiClient.login(externalUser.email);
    await acceptChatRequestViaApi(apiClient, conversation.id);

    // Step 5 — Verify message via API (external user can see the message)
    const messages = await getMessagesViaApi(apiClient, conversation.id);
    const msgList = Array.isArray(messages) ? messages : [];
    const businessMsg = (msgList as { content: string }[]).find(
      (m) => m.content === 'Message from business owner',
    );
    expect(businessMsg).toBeTruthy();

    // Step 6 — External user logs in → navigates to /chat → verify in UI
    const { page: extPage, context: extCtx } = await loginInNewContext(
      browser,
      externalUser.email,
      DEFAULT_PASSWORD,
    );
    const extChatPage = new ChatPage(extPage);
    await extChatPage.goto();

    // Step 7 — Click first conversation (should be the accepted DM)
    const firstConv = extChatPage.conversationList.getByRole('option').first();
    await expect(firstConv).toBeVisible({ timeout: 15000 });
    await firstConv.click();

    // Step 8 — Verify message from business owner in UI
    await expect(extPage.getByText('Message from business owner')).toBeVisible({ timeout: 10000 });

    // Step 9 — Reply as external user (Enter key to send)
    const msgPanel = new MessageViewPanel(extPage);
    await expect(msgPanel.messageInput).toBeVisible({ timeout: 10000 });
    await msgPanel.messageInput.fill('Reply from external user');
    await msgPanel.messageInput.press('Enter');
    await expect(extPage.getByText('Reply from external user')).toBeVisible({ timeout: 10000 });

    // Cleanup
    await extCtx.close();
  });
});
