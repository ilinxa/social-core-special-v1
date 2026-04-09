/**
 * Chat mute/unmute smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage } from '../../../pages/chat/chat.page';

test.describe('Chat Mute', () => {
  test('chat page loads for mute operations', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Mute toggle is inside conversation settings sheet
    await expect(chatPage.sidebarHeading).toBeVisible();
  });
});
