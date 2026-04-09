"use client";

import {
  ChatScopeProvider,
  type ChatScopeValue,
} from "@/features/chat/contexts/chat-scope-context";
import { ChatLayout } from "./ChatLayout";
import { ChatLayoutWrapper } from "./ChatLayoutWrapper";

interface ChatPageProps {
  scope: ChatScopeValue;
  showEntityInbox?: boolean;
}

/**
 * Shared page component for all chat routes.
 * Wraps ChatLayout with scope context and full-height layout override.
 */
export function ChatPage({ scope, showEntityInbox = false }: ChatPageProps) {
  return (
    <ChatScopeProvider value={scope}>
      <ChatLayoutWrapper>
        <ChatLayout showEntityInbox={showEntityInbox} />
      </ChatLayoutWrapper>
    </ChatScopeProvider>
  );
}
