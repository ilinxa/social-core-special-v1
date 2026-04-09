/**
 * Tests for chat optimistic update utilities.
 *
 * These utilities are pure cache-manipulation functions used by WS event
 * handlers and mutation hooks to keep TanStack Query caches in sync
 * without refetching from the server.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { QueryClient, type InfiniteData } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import type { PaginatedResponse } from "@/types";
import type {
  ChatMessage,
  ConversationListItem,
  LastMessage,
} from "@/features/chat/types";
import {
  insertMessageInCache,
  replaceMessageInCache,
  updateMessageInCache,
  updateReactionInCache,
  moveConversationToTop,
  incrementConversationUnread,
} from "../optimistic-updates";

// =============================================================================
// TEST HELPERS — factory functions for realistic mock data
// =============================================================================

let messageSeq = 0;

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  messageSeq += 1;
  return {
    id: `msg-${messageSeq}`,
    conversation_id: "conv-1",
    sender_type: "user",
    sender_id: "user-1",
    sender_name: "Alice",
    sender_avatar_url: null,
    content_type: "text",
    content: `Message ${messageSeq}`,
    status: "active",
    sequence_number: messageSeq,
    edited_at: null,
    created_at: new Date().toISOString(),
    attachments: [],
    reactions: { like: 0, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
    my_reactions: [],
    ...overrides,
  };
}

function makeConversation(
  overrides: Partial<ConversationListItem> = {},
): ConversationListItem {
  return {
    id: "conv-1",
    scope_type: "global",
    scope_id: null,
    conversation_type: "direct",
    name: "Test Conversation",
    last_message: null,
    unread_count: 0,
    is_muted: false,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeLastMessage(overrides: Partial<LastMessage> = {}): LastMessage {
  return {
    id: "msg-last",
    sender_type: "user",
    sender_id: "user-1",
    sender_name: "Alice",
    content_preview: "Hello!",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function buildMessageCache(
  pages: ChatMessage[][],
): InfiniteData<ChatMessage[]> {
  return {
    pages,
    pageParams: pages.map((_, i) => (i === 0 ? undefined : `cursor-${i}`)),
  };
}

function buildConversationCache(
  pages: PaginatedResponse<ConversationListItem>[],
): InfiniteData<PaginatedResponse<ConversationListItem>> {
  return {
    pages,
    pageParams: pages.map((_, i) => (i === 0 ? undefined : i + 1)),
  };
}

function makePaginatedPage(
  results: ConversationListItem[],
  overrides: Partial<PaginatedResponse<ConversationListItem>> = {},
): PaginatedResponse<ConversationListItem> {
  return {
    count: results.length,
    next: null,
    previous: null,
    results,
    ...overrides,
  };
}

// =============================================================================
// TEST SUITE
// =============================================================================

describe("optimistic-updates", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    messageSeq = 0;
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  // ---------------------------------------------------------------------------
  // insertMessageInCache
  // ---------------------------------------------------------------------------

  describe("insertMessageInCache", () => {
    it("prepends a new message to the first page", () => {
      const existing = makeMessage({ id: "existing-1" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[existing]]),
      );

      const newMsg = makeMessage({ id: "new-1", content: "Brand new" });
      insertMessageInCache(queryClient, "conv-1", newMsg);

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0]).toHaveLength(2);
      expect(data!.pages[0][0].id).toBe("new-1");
      expect(data!.pages[0][1].id).toBe("existing-1");
    });

    it("does not modify other pages", () => {
      const page1 = [makeMessage({ id: "p1-1" })];
      const page2 = [makeMessage({ id: "p2-1" }), makeMessage({ id: "p2-2" })];
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([page1, page2]),
      );

      const newMsg = makeMessage({ id: "new-1" });
      insertMessageInCache(queryClient, "conv-1", newMsg);

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[1]).toHaveLength(2);
      expect(data!.pages[1][0].id).toBe("p2-1");
    });

    it("handles empty first page gracefully", () => {
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[]]),
      );

      const newMsg = makeMessage({ id: "first-msg" });
      insertMessageInCache(queryClient, "conv-1", newMsg);

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0]).toHaveLength(1);
      expect(data!.pages[0][0].id).toBe("first-msg");
    });

    it("does nothing when cache is empty (undefined)", () => {
      insertMessageInCache(
        queryClient,
        "conv-nonexistent",
        makeMessage({ id: "orphan" }),
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-nonexistent"),
      );
      expect(data).toBeUndefined();
    });
  });

  // ---------------------------------------------------------------------------
  // replaceMessageInCache
  // ---------------------------------------------------------------------------

  describe("replaceMessageInCache", () => {
    it("replaces a message matching the predicate with the server message", () => {
      const optimistic = makeMessage({
        id: "temp-123",
        content: "Sending...",
      });
      const other = makeMessage({ id: "other-1" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[optimistic, other]]),
      );

      const serverMsg = makeMessage({
        id: "real-456",
        content: "Sent!",
        sequence_number: 99,
      });
      replaceMessageInCache(
        queryClient,
        "conv-1",
        (msg) => msg.id === "temp-123",
        serverMsg,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].id).toBe("real-456");
      expect(data!.pages[0][0].content).toBe("Sent!");
      expect(data!.pages[0][1].id).toBe("other-1");
    });

    it("searches across all pages for matching message", () => {
      const p1 = [makeMessage({ id: "p1-1" })];
      const p2 = [makeMessage({ id: "temp-in-p2" })];
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([p1, p2]),
      );

      const replacement = makeMessage({ id: "server-msg" });
      replaceMessageInCache(
        queryClient,
        "conv-1",
        (msg) => msg.id === "temp-in-p2",
        replacement,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[1][0].id).toBe("server-msg");
    });

    it("does not replace when predicate matches nothing", () => {
      const msg = makeMessage({ id: "stable" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      const replacement = makeMessage({ id: "should-not-appear" });
      replaceMessageInCache(
        queryClient,
        "conv-1",
        (m) => m.id === "nonexistent",
        replacement,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].id).toBe("stable");
    });

    it("does nothing when cache is empty (undefined)", () => {
      replaceMessageInCache(
        queryClient,
        "conv-x",
        () => true,
        makeMessage(),
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-x"),
      );
      expect(data).toBeUndefined();
    });
  });

  // ---------------------------------------------------------------------------
  // updateMessageInCache
  // ---------------------------------------------------------------------------

  describe("updateMessageInCache", () => {
    it("updates specific fields on the matching message", () => {
      const msg = makeMessage({
        id: "msg-to-edit",
        content: "Original",
        status: "active",
      });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateMessageInCache(queryClient, "conv-1", "msg-to-edit", {
        content: "Edited content",
        status: "edited",
        edited_at: "2026-03-26T10:00:00Z",
      });

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      const updated = data!.pages[0][0];
      expect(updated.content).toBe("Edited content");
      expect(updated.status).toBe("edited");
      expect(updated.edited_at).toBe("2026-03-26T10:00:00Z");
      // Untouched fields remain
      expect(updated.id).toBe("msg-to-edit");
      expect(updated.sender_name).toBe("Alice");
    });

    it("does not modify messages with different IDs", () => {
      const target = makeMessage({ id: "target" });
      const bystander = makeMessage({ id: "bystander", content: "Untouched" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[target, bystander]]),
      );

      updateMessageInCache(queryClient, "conv-1", "target", {
        content: "Changed",
      });

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][1].content).toBe("Untouched");
    });

    it("does nothing when cache is empty (undefined)", () => {
      updateMessageInCache(queryClient, "conv-nope", "msg-1", {
        content: "x",
      });

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-nope"),
      );
      expect(data).toBeUndefined();
    });
  });

  // ---------------------------------------------------------------------------
  // updateReactionInCache
  // ---------------------------------------------------------------------------

  describe("updateReactionInCache", () => {
    const CURRENT_USER = "user-me";

    it("increments reaction count when action is 'added'", () => {
      const msg = makeMessage({ id: "msg-react" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "like",
        "added",
        "user-other",
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].reactions.like).toBe(1);
    });

    it("adds reaction to my_reactions when the current user adds it", () => {
      const msg = makeMessage({ id: "msg-react" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "heart",
        "added",
        CURRENT_USER,
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].my_reactions).toContain("heart");
    });

    it("does not add to my_reactions when a different user adds a reaction", () => {
      const msg = makeMessage({ id: "msg-react" });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "laugh",
        "added",
        "user-other",
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].reactions.laugh).toBe(1);
      expect(data!.pages[0][0].my_reactions).not.toContain("laugh");
    });

    it("decrements reaction count when action is 'removed'", () => {
      const msg = makeMessage({
        id: "msg-react",
        reactions: { like: 3, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
      });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "like",
        "removed",
        "user-other",
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].reactions.like).toBe(2);
    });

    it("removes reaction from my_reactions when the current user removes it", () => {
      const msg = makeMessage({
        id: "msg-react",
        reactions: { like: 1, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
        my_reactions: ["like"],
      });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "like",
        "removed",
        CURRENT_USER,
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].reactions.like).toBe(0);
      expect(data!.pages[0][0].my_reactions).not.toContain("like");
    });

    it("does not let reaction count go below zero", () => {
      const msg = makeMessage({
        id: "msg-react",
        reactions: { like: 0, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
      });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "like",
        "removed",
        "user-other",
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      expect(data!.pages[0][0].reactions.like).toBe(0);
    });

    it("does not duplicate my_reactions if already present on add", () => {
      const msg = makeMessage({
        id: "msg-react",
        reactions: { like: 1, heart: 0, laugh: 0, wow: 0, sad: 0, angry: 0 },
        my_reactions: ["like"],
      });
      queryClient.setQueryData(
        queryKeys.chat.messages("conv-1"),
        buildMessageCache([[msg]]),
      );

      updateReactionInCache(
        queryClient,
        "conv-1",
        "msg-react",
        "like",
        "added",
        CURRENT_USER,
        CURRENT_USER,
      );

      const data = queryClient.getQueryData<InfiniteData<ChatMessage[]>>(
        queryKeys.chat.messages("conv-1"),
      );
      // Count should increment, but my_reactions should not duplicate
      expect(data!.pages[0][0].reactions.like).toBe(2);
      const likeOccurrences = data!.pages[0][0].my_reactions.filter(
        (r) => r === "like",
      );
      expect(likeOccurrences).toHaveLength(1);
    });
  });

  // ---------------------------------------------------------------------------
  // moveConversationToTop
  // ---------------------------------------------------------------------------

  describe("moveConversationToTop", () => {
    it("moves a conversation from first page to the top and updates last_message", () => {
      const conv1 = makeConversation({ id: "conv-1", name: "First" });
      const conv2 = makeConversation({ id: "conv-2", name: "Second" });
      const conv3 = makeConversation({ id: "conv-3", name: "Third" });

      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([
          makePaginatedPage([conv1, conv2, conv3], { count: 3 }),
        ]),
      );

      const newLastMsg = makeLastMessage({ content_preview: "New msg in conv-3" });
      moveConversationToTop(queryClient, "conv-3", newLastMsg);

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());

      const results = data!.pages[0].results;
      expect(results).toHaveLength(3);
      expect(results[0].id).toBe("conv-3");
      expect(results[0].last_message).toEqual(newLastMsg);
      expect(results[1].id).toBe("conv-1");
      expect(results[2].id).toBe("conv-2");
    });

    it("moves a conversation from a later page to top of first page", () => {
      const conv1 = makeConversation({ id: "conv-1" });
      const conv2 = makeConversation({ id: "conv-2" });
      const conv3 = makeConversation({ id: "conv-3" });

      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([
          makePaginatedPage([conv1], { count: 3, next: "page2" }),
          makePaginatedPage([conv2, conv3], { count: 3, previous: "page1" }),
        ]),
      );

      const newLastMsg = makeLastMessage({ content_preview: "Hello from page 2" });
      moveConversationToTop(queryClient, "conv-3", newLastMsg);

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());

      // First page should now have conv-3 at the top
      expect(data!.pages[0].results[0].id).toBe("conv-3");
      expect(data!.pages[0].results[0].last_message).toEqual(newLastMsg);
      // conv-1 shifts after conv-3
      expect(data!.pages[0].results[1].id).toBe("conv-1");
      // Second page should only have conv-2 remaining
      expect(data!.pages[1].results).toHaveLength(1);
      expect(data!.pages[1].results[0].id).toBe("conv-2");
    });

    it("does nothing when conversation is not found in cache", () => {
      const conv1 = makeConversation({ id: "conv-1" });
      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([makePaginatedPage([conv1])]),
      );

      const newLastMsg = makeLastMessage();
      moveConversationToTop(queryClient, "conv-nonexistent", newLastMsg);

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());

      // Should be unchanged
      expect(data!.pages[0].results).toHaveLength(1);
      expect(data!.pages[0].results[0].id).toBe("conv-1");
    });

    it("does nothing when cache is empty (undefined)", () => {
      const newLastMsg = makeLastMessage();
      moveConversationToTop(queryClient, "conv-1", newLastMsg);

      // No query data should exist
      const data = queryClient.getQueryData(queryKeys.chat.conversations());
      expect(data).toBeUndefined();
    });
  });

  // ---------------------------------------------------------------------------
  // incrementConversationUnread
  // ---------------------------------------------------------------------------

  describe("incrementConversationUnread", () => {
    it("increments unread_count on the matching conversation", () => {
      const conv = makeConversation({ id: "conv-1", unread_count: 2 });
      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([makePaginatedPage([conv])]),
      );

      incrementConversationUnread(queryClient, "conv-1");

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());
      expect(data!.pages[0].results[0].unread_count).toBe(3);
    });

    it("increments from zero correctly", () => {
      const conv = makeConversation({ id: "conv-1", unread_count: 0 });
      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([makePaginatedPage([conv])]),
      );

      incrementConversationUnread(queryClient, "conv-1");

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());
      expect(data!.pages[0].results[0].unread_count).toBe(1);
    });

    it("only increments the matching conversation, not others", () => {
      const conv1 = makeConversation({ id: "conv-1", unread_count: 5 });
      const conv2 = makeConversation({ id: "conv-2", unread_count: 0 });
      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([makePaginatedPage([conv1, conv2])]),
      );

      incrementConversationUnread(queryClient, "conv-1");

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());
      expect(data!.pages[0].results[0].unread_count).toBe(6);
      expect(data!.pages[0].results[1].unread_count).toBe(0);
    });

    it("works across multiple pages", () => {
      const conv1 = makeConversation({ id: "conv-1", unread_count: 1 });
      const conv2 = makeConversation({ id: "conv-2", unread_count: 3 });
      queryClient.setQueryData(
        queryKeys.chat.conversations(),
        buildConversationCache([
          makePaginatedPage([conv1], { count: 2, next: "page2" }),
          makePaginatedPage([conv2], { count: 2, previous: "page1" }),
        ]),
      );

      incrementConversationUnread(queryClient, "conv-2");

      const data = queryClient.getQueryData<
        InfiniteData<PaginatedResponse<ConversationListItem>>
      >(queryKeys.chat.conversations());
      // Page 1 untouched
      expect(data!.pages[0].results[0].unread_count).toBe(1);
      // Page 2 incremented
      expect(data!.pages[1].results[0].unread_count).toBe(4);
    });
  });
});
