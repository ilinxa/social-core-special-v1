/**
 * Chat API Functions
 * ==================
 * Typed async functions for all 30 chat REST endpoints.
 *
 * Backend source: apps.chat.urls (23 URL patterns), apps.chat.views (17 views)
 */

import { apiClient } from "@/lib/api-client";
import type { PaginatedResponse, PaginationParams } from "@/types";
import type {
  AddParticipantInput,
  BlockInput,
  ChatAttachment,
  ChatBlock,
  ChatMessage,
  ChatParticipant,
  ChatRequest,
  ConversationDetail,
  ConversationDetailWithPerms,
  ConversationListItem,
  ConversationListParams,
  CreateConversationInput,
  EditMessageInput,
  MarkSeenInput,
  MediaGalleryCursorParams,
  MediaGalleryResponse,
  MessageCursorParams,
  MessageSearchParams,
  MessageSearchResult,
  ReactionType,
  SendMessageInput,
  UnreadCounts,
  UpdateConversationInput,
} from "@/features/chat/types";

// =============================================================================
// CONVERSATIONS
// =============================================================================

export async function fetchConversationsApi(
  params?: ConversationListParams,
): Promise<PaginatedResponse<ConversationListItem>> {
  const response = await apiClient.get<PaginatedResponse<ConversationListItem>>(
    "/chat/conversations/",
    { params },
  );
  return response.data;
}

export async function createConversationApi(
  data: CreateConversationInput,
): Promise<ConversationDetailWithPerms> {
  const response = await apiClient.post<ConversationDetailWithPerms>(
    "/chat/conversations/",
    data,
  );
  return response.data;
}

export async function fetchConversationApi(
  conversationId: string,
): Promise<ConversationDetailWithPerms> {
  const response = await apiClient.get<ConversationDetailWithPerms>(
    `/chat/conversations/${conversationId}/`,
  );
  return response.data;
}

/** PATCH does NOT inject _permissions (only GET detail does) */
export async function updateConversationApi(
  conversationId: string,
  data: UpdateConversationInput,
): Promise<ConversationDetail> {
  const response = await apiClient.patch<ConversationDetail>(
    `/chat/conversations/${conversationId}/`,
    data,
  );
  return response.data;
}

export async function leaveConversationApi(
  conversationId: string,
): Promise<void> {
  await apiClient.post(`/chat/conversations/${conversationId}/leave/`);
}

export async function muteConversationApi(
  conversationId: string,
): Promise<void> {
  await apiClient.post(`/chat/conversations/${conversationId}/mute/`);
}

export async function unmuteConversationApi(
  conversationId: string,
): Promise<void> {
  await apiClient.post(`/chat/conversations/${conversationId}/unmute/`);
}

// =============================================================================
// PARTICIPANTS
// =============================================================================

export async function fetchParticipantsApi(
  conversationId: string,
): Promise<ChatParticipant[]> {
  const response = await apiClient.get<ChatParticipant[]>(
    `/chat/conversations/${conversationId}/participants/`,
  );
  return response.data;
}

export async function addParticipantApi(
  conversationId: string,
  data: AddParticipantInput,
): Promise<ChatParticipant> {
  const response = await apiClient.post<ChatParticipant>(
    `/chat/conversations/${conversationId}/participants/`,
    data,
  );
  return response.data;
}

/** participant_type is required in DELETE body (not just URL) */
export async function removeParticipantApi(
  conversationId: string,
  participantId: string,
  participantType: string,
): Promise<void> {
  await apiClient.delete(
    `/chat/conversations/${conversationId}/participants/${participantId}/`,
    { data: { participant_type: participantType } },
  );
}

export async function promoteParticipantApi(
  conversationId: string,
  participantId: string,
): Promise<void> {
  await apiClient.post(
    `/chat/conversations/${conversationId}/participants/${participantId}/promote/`,
  );
}

export async function demoteParticipantApi(
  conversationId: string,
  participantId: string,
): Promise<void> {
  await apiClient.post(
    `/chat/conversations/${conversationId}/participants/${participantId}/demote/`,
  );
}

// =============================================================================
// MESSAGES — returns raw JSON array, NOT paginated wrapper
// =============================================================================

/**
 * Fetch messages for a conversation.
 * Returns a raw array (NOT a paginated response).
 * Params: cursor (ISO8601), page_size (default 50, max 100), direction ("older"|"newer")
 */
export async function fetchMessagesApi(
  conversationId: string,
  params?: MessageCursorParams,
): Promise<ChatMessage[]> {
  const response = await apiClient.get<ChatMessage[]>(
    `/chat/conversations/${conversationId}/messages/`,
    { params },
  );
  return response.data;
}

export async function sendMessageApi(
  conversationId: string,
  data: SendMessageInput,
): Promise<ChatMessage> {
  const response = await apiClient.post<ChatMessage>(
    `/chat/conversations/${conversationId}/messages/`,
    data,
  );
  return response.data;
}

export async function editMessageApi(
  conversationId: string,
  messageId: string,
  data: EditMessageInput,
): Promise<ChatMessage> {
  const response = await apiClient.patch<ChatMessage>(
    `/chat/conversations/${conversationId}/messages/${messageId}/`,
    data,
  );
  return response.data;
}

export async function deleteMessageApi(
  conversationId: string,
  messageId: string,
): Promise<void> {
  await apiClient.delete(
    `/chat/conversations/${conversationId}/messages/${messageId}/`,
  );
}

// =============================================================================
// WATERMARKS
// =============================================================================

export async function markSeenApi(
  conversationId: string,
  data: MarkSeenInput,
): Promise<void> {
  await apiClient.post(`/chat/conversations/${conversationId}/seen/`, data);
}

// =============================================================================
// ATTACHMENTS — two-step upload: upload file → get ID → include in sendMessage
// =============================================================================

export async function uploadAttachmentApi(
  conversationId: string,
  file: File,
): Promise<ChatAttachment> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ChatAttachment>(
    `/chat/conversations/${conversationId}/upload/`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
}

// =============================================================================
// MEDIA GALLERY — custom { results, next_cursor } response
// =============================================================================

export async function fetchMediaGalleryApi(
  conversationId: string,
  params?: MediaGalleryCursorParams,
): Promise<MediaGalleryResponse> {
  const response = await apiClient.get<MediaGalleryResponse>(
    `/chat/conversations/${conversationId}/media/`,
    { params },
  );
  return response.data;
}

// =============================================================================
// REACTIONS — POST to add, DELETE to remove (both require { reaction } in body)
// =============================================================================

export async function addReactionApi(
  conversationId: string,
  messageId: string,
  reaction: ReactionType,
): Promise<void> {
  await apiClient.post(
    `/chat/conversations/${conversationId}/messages/${messageId}/reactions/`,
    { reaction },
  );
}

/** DELETE also requires { reaction } in body (same ReactionInputSerializer) */
export async function removeReactionApi(
  conversationId: string,
  messageId: string,
  reaction: ReactionType,
): Promise<void> {
  await apiClient.delete(
    `/chat/conversations/${conversationId}/messages/${messageId}/reactions/`,
    { data: { reaction } },
  );
}

// =============================================================================
// CHAT REQUESTS (global scope only)
// =============================================================================

export async function fetchChatRequestsApi(
  params?: PaginationParams,
): Promise<PaginatedResponse<ChatRequest>> {
  const response = await apiClient.get<PaginatedResponse<ChatRequest>>(
    "/chat/requests/",
    { params },
  );
  return response.data;
}

/** Returns HTTP 200 (not 204) */
export async function acceptChatRequestApi(
  conversationId: string,
): Promise<void> {
  await apiClient.post(`/chat/requests/${conversationId}/accept/`);
}

export async function ignoreChatRequestApi(
  conversationId: string,
): Promise<void> {
  await apiClient.post(`/chat/requests/${conversationId}/ignore/`);
}

// =============================================================================
// BLOCKS
// =============================================================================

export async function fetchBlocksApi(
  params?: PaginationParams,
): Promise<PaginatedResponse<ChatBlock>> {
  const response = await apiClient.get<PaginatedResponse<ChatBlock>>(
    "/chat/blocks/",
    { params },
  );
  return response.data;
}

export async function blockParticipantApi(
  data: BlockInput,
): Promise<ChatBlock> {
  const response = await apiClient.post<ChatBlock>("/chat/blocks/", data);
  return response.data;
}

export async function unblockParticipantApi(
  blockId: string,
): Promise<void> {
  await apiClient.delete(`/chat/blocks/${blockId}/`);
}

// =============================================================================
// ENTITY INBOX
// =============================================================================

export async function fetchEntityInboxApi(
  accountType: string,
  accountId: string,
  params?: PaginationParams,
): Promise<PaginatedResponse<ConversationListItem>> {
  const response = await apiClient.get<PaginatedResponse<ConversationListItem>>(
    `/chat/entity/${accountType}/${accountId}/inbox/`,
    { params },
  );
  return response.data;
}

// =============================================================================
// MESSAGE SEARCH
// =============================================================================

export async function searchMessagesApi(
  params: MessageSearchParams,
): Promise<PaginatedResponse<MessageSearchResult>> {
  const response = await apiClient.get<PaginatedResponse<MessageSearchResult>>(
    "/chat/messages/search/",
    { params },
  );
  return response.data;
}

// =============================================================================
// UNREAD COUNTS
// =============================================================================

/** Returns bare dict: { "global": 5, "business_<id>": 2, ... } */
export async function fetchUnreadCountsApi(): Promise<UnreadCounts> {
  const response = await apiClient.get<UnreadCounts>("/chat/unread/");
  return response.data;
}
