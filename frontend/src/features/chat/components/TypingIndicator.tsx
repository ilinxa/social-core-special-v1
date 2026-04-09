"use client";

import { useChatTypingUsers } from "@/stores/chat-store";

interface TypingIndicatorProps {
  conversationId: string;
}

/**
 * Displays who is typing in a conversation.
 *
 * - "Alice is typing..."
 * - "Alice and Bob are typing..."
 * - "Alice, Bob, and 2 others are typing..."
 */
export function TypingIndicator({ conversationId }: TypingIndicatorProps) {
  const typingUsers = useChatTypingUsers(conversationId);

  if (typingUsers.length === 0) return null;

  return (
    <div
      className="px-4 py-1.5"
      aria-live="polite"
      data-testid="typing-indicator"
    >
      <span className="text-xs text-muted-foreground">
        {formatTypingText(typingUsers)}
      </span>
    </div>
  );
}

function formatTypingText(userIds: string[]): string {
  const count = userIds.length;
  if (count === 0) return "";
  if (count === 1) return `Someone is typing...`;
  if (count === 2) return `2 people are typing...`;
  return `${count} people are typing...`;
}
