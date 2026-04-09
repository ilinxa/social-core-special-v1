"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useInView } from "react-intersection-observer";

import { Skeleton } from "@/components/ui/skeleton";
import { useMessages } from "@/features/chat/hooks/use-chat-queries";
import type { ConversationPermissions } from "@/features/chat/types";
import {
  groupMessages,
  type MessageListEntry,
} from "@/features/chat/utils/message-grouping";
import { DateSeparator } from "./DateSeparator";
import { EmptyMessages } from "./EmptyStates";
import { MessageBubble } from "./MessageBubble";
import { SystemMessage } from "./SystemMessage";

interface MessageListProps {
  conversationId: string;
  currentUserId: string;
  permissions: ConversationPermissions;
  isDm: boolean;
  onEditMessage?: (messageId: string, content: string) => void;
}

function MessageListSkeleton() {
  return (
    <div className="space-y-4 p-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex gap-2">
          <Skeleton className="h-6 w-6 shrink-0 rounded-full" />
          <div className="space-y-1">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-16 w-48 rounded-2xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MessageList({
  conversationId,
  currentUserId,
  permissions,
  isDm,
  onEditMessage,
}: MessageListProps) {
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useMessages(conversationId);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  // Load older messages trigger (at top of scroll area)
  const { ref: topRef, inView: topInView } = useInView({ threshold: 0 });
  useEffect(() => {
    if (topInView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [topInView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten pages into chronological order
  const allMessages = useMemo(() => {
    if (!data?.pages) return [];
    // Pages are in reverse chronological order (newest first in page 0).
    // Each page is chronological. Reverse page order for display.
    const reversed = [...data.pages].reverse();
    return reversed.flat();
  }, [data]);

  // Group messages for display
  const entries = useMemo(() => groupMessages(allMessages), [allMessages]);

  // Auto-scroll to bottom on new messages (only if already at bottom)
  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    const messageCount = allMessages.length;
    if (messageCount > prevMessageCountRef.current && prevMessageCountRef.current > 0) {
      // New message arrived — scroll if near bottom
      const container = scrollContainerRef.current;
      if (container) {
        const { scrollHeight, scrollTop, clientHeight } = container;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
        if (isNearBottom) {
          scrollToBottom();
        }
      }
    } else if (prevMessageCountRef.current === 0 && messageCount > 0) {
      // Initial load — scroll to bottom instantly
      bottomRef.current?.scrollIntoView();
    }
    prevMessageCountRef.current = messageCount;
  }, [allMessages.length, scrollToBottom]);

  if (isLoading) {
    return <MessageListSkeleton />;
  }

  if (allMessages.length === 0) {
    return <EmptyMessages />;
  }

  return (
    <div
      ref={scrollContainerRef}
      className="flex-1 overflow-y-auto"
      role="log"
      aria-label="Messages"
    >
      {/* Load older trigger */}
      {hasNextPage && (
        <div ref={topRef} className="py-2">
          {isFetchingNextPage && (
            <div className="flex justify-center py-2">
              <Skeleton className="h-4 w-4 animate-spin rounded-full" />
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="space-y-1 p-4">
        {entries.map((entry, index) => (
          <MessageListEntryRenderer
            key={entryKey(entry, index)}
            entry={entry}
            currentUserId={currentUserId}
            conversationId={conversationId}
            permissions={permissions}
            isDm={isDm}
            onEditMessage={onEditMessage}
          />
        ))}
      </div>

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}

// =============================================================================
// ENTRY RENDERER
// =============================================================================

function MessageListEntryRenderer({
  entry,
  currentUserId,
  conversationId,
  permissions,
  isDm,
  onEditMessage,
}: {
  entry: MessageListEntry;
  currentUserId: string;
  conversationId: string;
  permissions: ConversationPermissions;
  isDm: boolean;
  onEditMessage?: (messageId: string, content: string) => void;
}) {
  if (entry.type === "date") {
    return <DateSeparator date={entry.date} />;
  }

  return (
    <div className="space-y-0.5">
      {entry.messages.map((msg, i) => {
        if (msg.content_type === "system") {
          return <SystemMessage key={msg.id} content={msg.content} />;
        }
        return (
          <MessageBubble
            key={msg.id}
            message={msg}
            isOwn={msg.sender_id === currentUserId}
            showSender={i === 0}
            conversationId={conversationId}
            permissions={permissions}
            isDm={isDm}
            onEditMessage={onEditMessage}
          />
        );
      })}
    </div>
  );
}

function entryKey(entry: MessageListEntry, index: number): string {
  if (entry.type === "date") return `date-${index}`;
  return `group-${entry.messages[0].id}`;
}
