"use client";

import { useCallback, useState } from "react";

import { useChatScope } from "@/features/chat/contexts/chat-scope-context";
import { useConversation } from "@/features/chat/hooks/use-chat-queries";
import { useChatStore } from "@/stores/chat-store";
import { useUser } from "@/stores/auth-store";
import type { ConversationPermissions, MessageSearchResult } from "@/features/chat/types";
import { ComposeBar } from "./ComposeBar";
import { ConversationSettings } from "./ConversationSettings";
import { EditMessageMode } from "./EditMessageMode";
import { MessageList } from "./MessageList";
import { MessageSearchPanel } from "./MessageSearchPanel";
import { MessageViewHeader } from "./MessageViewHeader";
import { RequestBanner } from "./RequestBanner";
import { TypingIndicator } from "./TypingIndicator";
import { NoConversationSelected } from "./EmptyStates";

interface MessageViewProps {
  conversationId: string | null;
  onBack: () => void;
}

export function MessageView({ conversationId, onBack }: MessageViewProps) {
  const user = useUser();

  if (!conversationId) {
    return <NoConversationSelected />;
  }

  return (
    <MessageViewInner
      conversationId={conversationId}
      currentUserId={user?.id ?? ""}
      onBack={onBack}
    />
  );
}

function MessageViewInner({
  conversationId,
  currentUserId,
  onBack,
}: {
  conversationId: string;
  currentUserId: string;
  onBack: () => void;
}) {
  const { scopeType, scopeId } = useChatScope();
  const { data: conversation, isLoading } = useConversation(conversationId);
  const setActiveConversation = useChatStore((s) => s.setActiveConversation);

  const [showSettings, setShowSettings] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [editingMessage, setEditingMessage] = useState<{
    id: string;
    content: string;
  } | null>(null);

  const handleEditMessage = useCallback((messageId: string, content: string) => {
    setEditingMessage({ id: messageId, content });
  }, []);

  const handleEditComplete = useCallback(() => {
    setEditingMessage(null);
  }, []);

  const handleSearchResultClick = useCallback(
    (result: MessageSearchResult) => {
      // Navigate to the conversation containing the search result
      setActiveConversation(result.conversation_id);
      setShowSearch(false);
    },
    [setActiveConversation],
  );

  const handleLeft = useCallback(() => {
    setShowSettings(false);
    setActiveConversation(null);
    onBack();
  }, [setActiveConversation, onBack]);

  if (isLoading || !conversation) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const permissions: ConversationPermissions = conversation._permissions ?? {
    can_send_message: false,
    can_view_messages: false,
    can_leave: false,
    can_manage_group: false,
    can_add_participant: false,
    can_remove_participant: false,
    can_edit_group: false,
  };
  const canSend = permissions.can_send_message;
  const isDm = conversation.conversation_type === "direct";

  // Check if this is a pending request for the current user
  const myParticipant = conversation.participants.find(
    (p) => p.participant_id === currentUserId && p.participant_type === "user",
  );
  const isPendingRequest = myParticipant?.request_status === "pending";

  return (
    <div className="flex h-full">
      {/* Main message column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <MessageViewHeader
          conversation={conversation}
          onBack={onBack}
          onOpenSettings={() => setShowSettings(true)}
          onOpenSearch={() => setShowSearch(!showSearch)}
        />

        {/* Request banner */}
        {isPendingRequest && (
          <RequestBanner conversationId={conversationId} />
        )}

        <MessageList
          conversationId={conversationId}
          currentUserId={currentUserId}
          permissions={permissions}
          isDm={isDm}
          onEditMessage={handleEditMessage}
        />

        <TypingIndicator conversationId={conversationId} />

        {/* Edit mode or compose bar */}
        {editingMessage ? (
          <EditMessageMode
            conversationId={conversationId}
            messageId={editingMessage.id}
            initialContent={editingMessage.content}
            onCancel={handleEditComplete}
            onComplete={handleEditComplete}
          />
        ) : (
          <ComposeBar
            conversationId={conversationId}
            disabled={!canSend}
            disabledMessage={
              !canSend
                ? "You don't have permission to send messages"
                : undefined
            }
          />
        )}
      </div>

      {/* Search panel (slide-in from right) */}
      {showSearch && (
        <div className="hidden w-72 border-l md:block">
          <MessageSearchPanel
            scopeType={scopeType}
            scopeId={scopeId ?? undefined}
            onResultClick={handleSearchResultClick}
            onClose={() => setShowSearch(false)}
          />
        </div>
      )}

      {/* Settings sheet */}
      <ConversationSettings
        conversation={conversation}
        currentUserId={currentUserId}
        open={showSettings}
        onOpenChange={setShowSettings}
        onLeft={handleLeft}
      />
    </div>
  );
}
