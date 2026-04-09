"use client";

import { MessageCircle, MessageSquarePlus, MessagesSquare } from "lucide-react";

import { Button } from "@/components/ui/button";

// =============================================================================
// EMPTY CONVERSATION LIST
// =============================================================================

interface EmptyConversationListProps {
  onNewConversation?: () => void;
}

export function EmptyConversationList({ onNewConversation }: EmptyConversationListProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="rounded-full bg-muted p-4">
        <MessagesSquare className="h-8 w-8 text-muted-foreground" />
      </div>
      <div>
        <p className="font-medium">No conversations yet</p>
        <p className="text-sm text-muted-foreground">
          Start a conversation to begin chatting
        </p>
      </div>
      {onNewConversation && (
        <Button size="sm" onClick={onNewConversation}>
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          New conversation
        </Button>
      )}
    </div>
  );
}

// =============================================================================
// EMPTY MESSAGES
// =============================================================================

export function EmptyMessages() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="rounded-full bg-muted p-3">
        <MessageCircle className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm text-muted-foreground">
        Send a message to start the conversation
      </p>
    </div>
  );
}

// =============================================================================
// NO CONVERSATION SELECTED (desktop right panel)
// =============================================================================

export function NoConversationSelected() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="rounded-full bg-muted p-4">
        <MessagesSquare className="h-8 w-8 text-muted-foreground" />
      </div>
      <div>
        <p className="font-medium">Select a conversation</p>
        <p className="text-sm text-muted-foreground">
          Choose a conversation from the sidebar to start chatting
        </p>
      </div>
    </div>
  );
}
