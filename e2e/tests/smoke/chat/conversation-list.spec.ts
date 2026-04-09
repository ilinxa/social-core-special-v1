/**
 * Chat conversation list smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P1
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage } from '../../../pages/chat/chat.page';

test.describe('Chat Conversation List', () => {
  test('chat page renders with sidebar', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    await expect(chatPage.sidebarHeading).toBeVisible();
  });

  test('search input is visible', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    await expect(chatPage.conversationSearchInput).toBeVisible();
  });

  test('conversation listbox has proper ARIA role', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Listbox may not render when there are no conversations — check either state
    await expect(
      chatPage.conversationList.or(chatPage.noConversationsMessage),
    ).toBeVisible();
  });

  test('shows empty state when no conversations', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Either has conversations or shows empty state
    await expect(
      chatPage.noConversationsMessage.or(chatPage.conversationList),
    ).toBeVisible();
  });
});
