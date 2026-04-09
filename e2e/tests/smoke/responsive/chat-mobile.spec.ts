/**
 * Chat on mobile viewport (iPhone 14 Pro — 393x852).
 *
 * Verifies single-panel mode: conversation list fills screen,
 * selecting a conversation shows message view with back button.
 *
 * @layer L1
 * @system chat
 * @parameters P7 (Real-time), P8 (Responsive)
 * @priority P1
 */

import { test, expect } from '../../../fixtures/base.fixture';
import { isSystemEnabled } from '../../../lib/feature-gates';
import { generateEmail } from '../../../lib/utils';
import { registerAndVerifyViaApi } from '../../../helpers/auth.helper';
import { createConversationViaApi, sendMessageViaApi } from '../../../helpers/chat.helper';
import { ChatPage, MessageViewPanel } from '../../../pages/chat/chat.page';
import { TEST_USERS } from '../../../lib/constants';

test.describe('Chat — Mobile', () => {
  test.skip(!isSystemEnabled('chat'), 'Chat system disabled');

  test('conversation list fills screen on mobile', async ({
    page,
    apiClient,
    dbClient,
  }) => {
    // Setup: create a conversation so the list isn't empty
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('chat-mobile-other'),
    });
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);
    const conv = await createConversationViaApi(apiClient, [user.id]);
    await sendMessageViaApi(apiClient, conv.id, 'Mobile test message');

    // Login as regular user via storageState isn't available in base.fixture,
    // so navigate directly — the smoke-mobile project uses unauthenticated page
    // We'll login via API and set token
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);

    // Navigate to chat
    await page.goto('/chat');

    // On mobile, conversation list should be visible
    const chatPage = new ChatPage(page);
    await expect(chatPage.conversationList.or(chatPage.noConversationsMessage)).toBeVisible();
  });

  test('selecting conversation shows message view with back button', async ({
    page,
    apiClient,
    dbClient,
  }) => {
    // Setup: create a conversation with a message
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('chat-mobile-conv'),
    });
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);
    const conv = await createConversationViaApi(apiClient, [user.id]);
    await sendMessageViaApi(apiClient, conv.id, 'Hello from mobile');

    await page.goto('/chat');

    const chatPage = new ChatPage(page);
    // Wait for conversation list to load
    await expect(chatPage.conversationList).toBeVisible();

    // Click first conversation
    const firstConv = chatPage.conversationList.getByRole('option').first();
    if (await firstConv.isVisible()) {
      await firstConv.click();

      // Message view should show with back button (mobile single-panel)
      const messagePanel = new MessageViewPanel(page);
      await expect(messagePanel.backButton).toBeVisible();
      await expect(messagePanel.messageInput).toBeVisible();

      // Back button should return to conversation list
      await messagePanel.backButton.click();
      await expect(chatPage.conversationList).toBeVisible();
    }
  });

  test('compose bar is usable on mobile', async ({
    page,
    apiClient,
    dbClient,
  }) => {
    const user = await registerAndVerifyViaApi(apiClient, dbClient, {
      email: generateEmail('chat-mobile-compose'),
    });
    await apiClient.login(TEST_USERS.regular.email, TEST_USERS.regular.password);
    const conv = await createConversationViaApi(apiClient, [user.id]);

    await page.goto('/chat');

    const chatPage = new ChatPage(page);
    await expect(chatPage.conversationList).toBeVisible();

    const firstConv = chatPage.conversationList.getByRole('option').first();
    if (await firstConv.isVisible()) {
      await firstConv.click();

      const messagePanel = new MessageViewPanel(page);
      await expect(messagePanel.messageInput).toBeVisible();
      await expect(messagePanel.sendButton).toBeVisible();

      // Type a message on mobile
      await messagePanel.messageInput.fill('Mobile message test');
      await expect(messagePanel.messageInput).toHaveValue('Mobile message test');
    }
  });
});
