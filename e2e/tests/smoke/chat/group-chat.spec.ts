/**
 * Chat group conversation smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage, NewConversationDialog } from '../../../pages/chat/chat.page';

test.describe('Group Chat', () => {
  test('new conversation dialog opens', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    await chatPage.newConversationButton.click();

    const dialog = new NewConversationDialog(page);
    await expect(dialog.title).toBeVisible();
    await expect(dialog.userSearchInput).toBeVisible();
  });

  test('new conversation dialog has create and cancel buttons', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    await chatPage.newConversationButton.click();

    const dialog = new NewConversationDialog(page);
    await expect(dialog.cancelButton).toBeVisible();
  });
});
