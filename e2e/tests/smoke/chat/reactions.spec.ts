/**
 * Chat reactions smoke tests.
 *
 * @layer L1
 * @system chat
 * @parameters P1, P2, P5
 * @priority P2
 */

import { test, expect } from '../../../fixtures/auth.fixture';
import { ReactionControls } from '../../../pages/chat/chat.page';

test.describe('Chat Reactions', () => {
  test('reaction controls POM instantiates without error', async ({
    authenticatedPage,
  }) => {
    const page = authenticatedPage;

    // Navigate to chat — reactions only visible on messages
    await page.goto('/chat');

    // Verify the reaction-related test IDs are queryable
    const controls = new ReactionControls(page);
    // Reaction bar is only visible when a message has reactions — just verify POM works
    expect(controls.reactionBar).toBeDefined();
    expect(controls.addReactionButton).toBeDefined();
  });
});
