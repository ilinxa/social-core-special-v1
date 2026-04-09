/**
 * Chat Query Hooks
 * ================
 * TanStack Query hooks for all chat read operations.
 *
 * Three distinct pagination patterns:
 * 1. StandardPagination (page-number) — conversations, requests, blocks, entity inbox, search
 * 2. Custom message cursor — raw array response, manual cursor tracking
 * 3. Custom media cursor — { results, next_cursor }
 */

import {
  queryOptions,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  fetchConversationsApi,
  fetchConversationApi,
  fetchParticipantsApi,
  fetchMessagesApi,
  fetchMediaGalleryApi,
  fetchChatRequestsApi,
  fetchBlocksApi,
  fetchEntityInboxApi,
  searchMessagesApi,
  fetchUnreadCountsApi,
} from "@/features/chat/api/chat-api";
import { MESSAGES_PAGE_SIZE, MEDIA_GALLERY_PAGE_SIZE } from "@/features/chat/constants/chat-constants";
import type {
  ConversationListParams,
  MessageSearchParams,
} from "@/features/chat/types";

// =============================================================================
// HELPERS
// =============================================================================

/** Extract page number from a DRF pagination `next` URL, or undefined. */
function getNextPage(nextUrl: string | null): number | undefined {
  if (!nextUrl) return undefined;
  try {
    const url = new URL(nextUrl);
    const page = url.searchParams.get("page");
    return page ? Number(page) : undefined;
  } catch {
    return undefined;
  }
}

// =============================================================================
// QUERY OPTION FACTORIES
// =============================================================================

export function conversationDetailQueryOptions(conversationId: string) {
  return queryOptions({
    queryKey: queryKeys.chat.conversation(conversationId),
    queryFn: () => fetchConversationApi(conversationId),
    staleTime: 5 * 60 * 1000,
    enabled: !!conversationId,
  });
}

export function participantsQueryOptions(conversationId: string) {
  return queryOptions({
    queryKey: queryKeys.chat.participants(conversationId),
    queryFn: () => fetchParticipantsApi(conversationId),
    staleTime: 60 * 1000,
    enabled: !!conversationId,
  });
}

export function unreadCountsQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.chat.unread(),
    queryFn: fetchUnreadCountsApi,
    staleTime: 30 * 1000,
    refetchInterval: 30_000,
  });
}

// =============================================================================
// QUERY HOOKS
// =============================================================================

/** Infinite-scroll conversation list. StandardPagination (page-number). */
export function useConversations(
  params?: Omit<ConversationListParams, "page">,
) {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.conversations(params),
    queryFn: ({ pageParam }) =>
      fetchConversationsApi({ ...params, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
  });
}

/** Single conversation detail with _permissions. */
export function useConversation(conversationId: string) {
  return useQuery(conversationDetailQueryOptions(conversationId));
}

/** Unpaginated participant list for a conversation. */
export function useParticipants(conversationId: string) {
  return useQuery(participantsQueryOptions(conversationId));
}

/**
 * Infinite-scroll message list. Custom cursor pagination.
 *
 * Response is a raw array ChatMessage[] (NOT a paginated wrapper).
 * Cursor = created_at of oldest loaded message.
 * Direction: "older" for scrolling up (loading history).
 */
export function useMessages(conversationId: string) {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.messages(conversationId),
    queryFn: ({ pageParam }) =>
      fetchMessagesApi(conversationId, {
        cursor: pageParam,
        page_size: MESSAGES_PAGE_SIZE,
        direction: "older",
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      // If fewer items than page_size, no more pages
      if (lastPage.length < MESSAGES_PAGE_SIZE) return undefined;
      // Use created_at of the oldest message as cursor for next page
      const oldest = lastPage[lastPage.length - 1];
      return oldest?.created_at;
    },
    staleTime: 60 * 1000,
    enabled: !!conversationId,
  });
}

/**
 * Infinite-scroll media gallery. Custom cursor pagination.
 *
 * Response is { results: ChatAttachment[], next_cursor: string | null }.
 */
export function useMediaGallery(conversationId: string) {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.mediaGallery(conversationId),
    queryFn: ({ pageParam }) =>
      fetchMediaGalleryApi(conversationId, {
        cursor: pageParam,
        page_size: MEDIA_GALLERY_PAGE_SIZE,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 60 * 1000,
    enabled: !!conversationId,
  });
}

/** Infinite-scroll chat requests. StandardPagination. */
export function useChatRequests() {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.requests(),
    queryFn: ({ pageParam }) =>
      fetchChatRequestsApi({ page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
  });
}

/** Infinite-scroll chat blocks. StandardPagination. */
export function useChatBlocks() {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.blocks(),
    queryFn: ({ pageParam }) =>
      fetchBlocksApi({ page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 60 * 1000,
  });
}

/** Infinite-scroll entity inbox. StandardPagination. */
export function useEntityInbox(accountType: string, accountId: string) {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.entityInbox(accountType, accountId),
    queryFn: ({ pageParam }) =>
      fetchEntityInboxApi(accountType, accountId, { page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
    enabled: !!accountType && !!accountId,
  });
}

/** Infinite-scroll message search. StandardPagination. */
export function useMessageSearch(
  params: Omit<MessageSearchParams, "page">,
) {
  return useInfiniteQuery({
    queryKey: queryKeys.chat.search(params),
    queryFn: ({ pageParam }) =>
      searchMessagesApi({ ...params, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => getNextPage(lastPage.next),
    staleTime: 30 * 1000,
    enabled: !!params.q && params.q.length >= 2,
  });
}

/** Unread counts with polling fallback (30s). */
export function useUnreadCounts() {
  return useQuery(unreadCountsQueryOptions());
}
