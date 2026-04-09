"use client";

import { useCallback, useState } from "react";

import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chat-store";
import { useChatWs } from "@/features/chat/hooks/use-chat-ws";
import { ChatWsProvider } from "@/features/chat/contexts/chat-ws-context";
import { ConnectionBanner } from "./ConnectionBanner";
import { ConversationList } from "./ConversationList";
import { MessageView } from "./MessageView";
import { NewConversationDialog } from "./NewConversationDialog";

interface ChatLayoutProps {
  showEntityInbox?: boolean;
}

/**
 * Responsive dual-panel chat layout.
 *
 * Desktop (>= md): sidebar (320px) + message view (flex-1).
 * Mobile (< md): shows EITHER conversation list OR message view,
 *   controlled by activeConversationId.
 *
 * Initializes the WebSocket connection and provides it via context.
 */
export function ChatLayout({ showEntityInbox = false }: ChatLayoutProps) {
  const ws = useChatWs();
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const setActiveConversation = useChatStore((s) => s.setActiveConversation);
  const [showNewDialog, setShowNewDialog] = useState(false);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversation(id);
    },
    [setActiveConversation],
  );

  const handleBack = useCallback(() => {
    setActiveConversation(null);
  }, [setActiveConversation]);

  const hasActiveConversation = !!activeConversationId;

  return (
    <ChatWsProvider value={ws}>
      <ConnectionBanner />
      <div className="flex min-h-0 flex-1">
        {/* Sidebar — hidden on mobile when conversation is open */}
        <div
          className={cn(
            "h-full w-full border-r md:block md:w-80 md:shrink-0",
            hasActiveConversation && "hidden",
          )}
        >
          <ConversationList
            activeConversationId={activeConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={() => setShowNewDialog(true)}
            showEntityInbox={showEntityInbox}
          />
        </div>

        {/* Message view — hidden on mobile when no conversation */}
        <div
          className={cn(
            "h-full min-w-0 flex-1",
            !hasActiveConversation && "hidden md:flex",
          )}
        >
          <MessageView
            conversationId={activeConversationId}
            onBack={handleBack}
          />
        </div>
      </div>

      <NewConversationDialog
        open={showNewDialog}
        onOpenChange={setShowNewDialog}
        onCreated={handleSelectConversation}
      />
    </ChatWsProvider>
  );
}
