/**
 * Optimistic Update Utilities
 * ===========================
 * Pure functions for TanStack Query cache manipulation.
 *
 * Used by WS event handlers and mutation hooks to update the
 * message/conversation caches without refetching from the server.
 */

import type { InfiniteData, QueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import type {
  ChatMessage,
  ConversationListItem,
  LastMessage,
  ReactionType,
} from "@/features/chat/types";
import type { PaginatedResponse } from "@/types";

// =============================================================================
// MESSAGE CACHE OPERATIONS
// =============================================================================

/**
 * Insert a new message into the TQ infinite messages cache.
 * The message is prepended to the first page (newest messages).
 */
export function insertMessageInCache(
  queryClient: QueryClient,
  conversationId: string,
  message: ChatMessage,
): void {
  queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
    queryKeys.chat.messages(conversationId),
    (old) => {
      if (!old) return old;
      const pages = [...old.pages];
      // First page contains the newest messages — prepend there
      pages[0] = [message, ...(pages[0] ?? [])];
      return { ...old, pages };
    },
  );
}

/**
 * Replace an optimistic (temp) message with the real server message.
 * Matches by a predicate function (e.g., temp ID or sequence_number).
 */
export function replaceMessageInCache(
  queryClient: QueryClient,
  conversationId: string,
  predicate: (msg: ChatMessage) => boolean,
  serverMessage: ChatMessage,
): void {
  queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
    queryKeys.chat.messages(conversationId),
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map((page) =>
          page.map((msg) => (predicate(msg) ? serverMessage : msg)),
        ),
      };
    },
  );
}

/**
 * Update fields on a specific message in cache (by message ID).
 */
export function updateMessageInCache(
  queryClient: QueryClient,
  conversationId: string,
  messageId: string,
  updates: Partial<ChatMessage>,
): void {
  queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
    queryKeys.chat.messages(conversationId),
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map((page) =>
          page.map((msg) =>
            msg.id === messageId ? { ...msg, ...updates } : msg,
          ),
        ),
      };
    },
  );
}

/**
 * Update reaction counts on a message in cache.
 */
export function updateReactionInCache(
  queryClient: QueryClient,
  conversationId: string,
  messageId: string,
  reaction: ReactionType,
  action: "added" | "removed",
  userId: string,
  currentUserId: string,
): void {
  queryClient.setQueryData<InfiniteData<ChatMessage[]>>(
    queryKeys.chat.messages(conversationId),
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map((page) =>
          page.map((msg) => {
            if (msg.id !== messageId) return msg;

            const reactions = { ...msg.reactions };
            const myReactions = [...msg.my_reactions];

            if (action === "added") {
              reactions[reaction] = (reactions[reaction] ?? 0) + 1;
              if (userId === currentUserId && !myReactions.includes(reaction)) {
                myReactions.push(reaction);
              }
            } else {
              reactions[reaction] = Math.max(0, (reactions[reaction] ?? 0) - 1);
              if (userId === currentUserId) {
                const idx = myReactions.indexOf(reaction);
                if (idx !== -1) myReactions.splice(idx, 1);
              }
            }

            return { ...msg, reactions, my_reactions: myReactions };
          }),
        ),
      };
    },
  );
}

// =============================================================================
// CONVERSATION LIST CACHE OPERATIONS
// =============================================================================

/**
 * Move a conversation to the top of the list and update its last_message.
 * Works across all conversation list queries (different scope params).
 */
export function moveConversationToTop(
  queryClient: QueryClient,
  conversationId: string,
  lastMessage: LastMessage,
): void {
  // Update ALL conversation list queries (different scope params)
  queryClient.setQueriesData<InfiniteData<PaginatedResponse<ConversationListItem>>>(
    { queryKey: queryKeys.chat.conversations() },
    (old) => {
      if (!old) return old;

      // Find the conversation across pages
      let foundConv: ConversationListItem | undefined;
      const pagesWithout = old.pages.map((page) => ({
        ...page,
        results: page.results.filter((c) => {
          if (c.id === conversationId) {
            foundConv = c;
            return false;
          }
          return true;
        }),
      }));

      if (!foundConv) return old;

      // Put the updated conversation at the top of page 0
      const updated: ConversationListItem = {
        ...foundConv,
        last_message: lastMessage,
      };
      pagesWithout[0] = {
        ...pagesWithout[0],
        results: [updated, ...pagesWithout[0].results],
      };

      return { ...old, pages: pagesWithout };
    },
  );
}

/**
 * Increment unread count for a conversation in list cache.
 */
export function incrementConversationUnread(
  queryClient: QueryClient,
  conversationId: string,
): void {
  queryClient.setQueriesData<InfiniteData<PaginatedResponse<ConversationListItem>>>(
    { queryKey: queryKeys.chat.conversations() },
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map((page) => ({
          ...page,
          results: page.results.map((c) =>
            c.id === conversationId
              ? { ...c, unread_count: c.unread_count + 1 }
              : c,
          ),
        })),
      };
    },
  );
}
