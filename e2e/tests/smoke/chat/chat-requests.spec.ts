/**
 * Chat requests smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P3, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ChatPage, ChatRequestsPanel } from '../../../pages/chat/chat.page';

test.describe('Chat Requests', () => {
  test('chat page renders without error', async ({ authenticatedPage }) => {
    const page = authenticatedPage;
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Chat requests section only visible when there are pending requests
    const requests = new ChatRequestsPanel(page);
    // Verify the request section is either visible (with requests) or absent
    const isVisible = await requests.requestList.isVisible();
    if (isVisible) {
      await expect(requests.requestHeading).toBeVisible();
    }
  });
});
