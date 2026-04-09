/**
 * Chat System Types
 * =================
 * TypeScript types matching backend chat serializer shapes exactly.
 *
 * Backend source: apps.chat.serializers, apps.chat.constants,
 * apps.chat.consumers, apps.chat.ws_serializers
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// ENUMS (union literal types matching backend TextChoices)
// =============================================================================

export type ScopeType = "global" | "business" | "platform";

export type ConversationType = "direct" | "group";

export type ParticipantType = "user" | "business" | "platform";

export type ParticipantRole = "member" | "admin";

export type RequestStatus = "none" | "pending" | "accepted" | "ignored" | "blocked";

export type MessageContentType = "text" | "system" | "image";

export type MessageStatus = "active" | "edited" | "deleted";

export type ReactionType = "like" | "heart" | "laugh" | "wow" | "sad" | "angry";

export type AttachmentType = "image";

// =============================================================================
// DOMAIN TYPES — matching backend output serializers exactly
// =============================================================================

/** ParticipantOutputSerializer fields */
export type ChatParticipant = {
  id: string;
  participant_type: ParticipantType;
  participant_id: string;
  display_name: string;
  avatar_url: string | null;
  role: ParticipantRole;
  request_status: RequestStatus;
  is_muted: boolean;
  is_active: boolean;
  created_at: string;
};

/** LastMessageSerializer fields */
export type LastMessage = {
  id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  content_preview: string;
  created_at: string;
};

/** ConversationListOutputSerializer fields — includes computed unread_count + is_muted */
export type ConversationListItem = {
  id: string;
  scope_type: ScopeType;
  scope_id: string | null;
  conversation_type: ConversationType;
  name: string;
  last_message: LastMessage | null;
  unread_count: number;
  is_muted: boolean;
  created_at: string;
};

/** ConversationDetailOutputSerializer fields — NO unread_count, NO is_muted */
export type ConversationDetail = {
  id: string;
  scope_type: ScopeType;
  scope_id: string | null;
  conversation_type: ConversationType;
  name: string;
  description: string;
  participants: ChatParticipant[];
  last_message: LastMessage | null;
  is_active: boolean;
  created_at: string;
};

/** AttachmentOutputSerializer fields */
export type ChatAttachment = {
  id: string;
  file_type: AttachmentType;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  url: string;
};

/** MessageOutputSerializer fields — reactions + my_reactions present in REST, absent in WS */
export type ChatMessage = {
  id: string;
  conversation_id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  sender_avatar_url: string | null;
  content_type: MessageContentType;
  content: string;
  status: MessageStatus;
  sequence_number: number;
  edited_at: string | null;
  created_at: string;
  attachments: ChatAttachment[];
  reactions: Record<ReactionType, number>;
  my_reactions: ReactionType[];
};

/** ChatRequestOutputSerializer fields */
export type ChatRequest = {
  conversation_id: string;
  requester: {
    participant_type: ParticipantType;
    participant_id: string;
    display_name: string;
    avatar_url: string | null;
  } | null;
  preview_messages: Array<{
    content: string;
    created_at: string;
  }>;
  message_count: number;
  created_at: string;
};

/** ChatBlockOutputSerializer fields */
export type ChatBlock = {
  id: string;
  blocked_type: ParticipantType;
  blocked_id: string;
  blocked_name: string;
  created_at: string;
};

/** MessageSearchOutputSerializer fields */
export type MessageSearchResult = {
  id: string;
  conversation_id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  content: string;
  status: MessageStatus;
  sequence_number: number;
  created_at: string;
  conversation_name: string;
};

// =============================================================================
// PERMISSIONS — 7 booleans from ChatPolicy.get_viewer_permissions()
// =============================================================================

export type ConversationPermissions = {
  can_send_message: boolean;
  can_view_messages: boolean;
  can_leave: boolean;
  can_manage_group: boolean;
  can_add_participant: boolean;
  can_remove_participant: boolean;
  can_edit_group: boolean;
};

export type ConversationDetailWithPerms = ConversationDetail &
  WithPermissions<ConversationPermissions>;

// =============================================================================
// INPUT TYPES — matching backend input serializers
// =============================================================================

export type ParticipantIdInput = {
  participant_type: ParticipantType;
  participant_id: string;
};

export type CreateConversationInput = {
  scope_type: ScopeType;
  scope_id?: string | null;
  conversation_type: ConversationType;
  participant_ids: ParticipantIdInput[];
  name?: string;
};

export type SendMessageInput = {
  content?: string;
  content_type?: MessageContentType;
  sender_type?: ParticipantType;
  sender_id?: string;
  attachment_ids?: string[];
};

export type EditMessageInput = {
  content: string;
};

export type UpdateConversationInput = {
  name?: string;
  description?: string;
};

export type AddParticipantInput = {
  participant_type: ParticipantType;
  participant_id: string;
};

export type BlockInput = {
  blocked_type: ParticipantType;
  blocked_id: string;
};

export type MarkSeenInput = {
  last_seen_message_id: string;
};

// =============================================================================
// PAGINATION TYPES — 3 distinct patterns
// =============================================================================

/** Custom message cursor params (raw array response) */
export type MessageCursorParams = {
  cursor?: string;
  page_size?: number;
  direction?: "older" | "newer";
};

/** Custom media gallery response */
export type MediaGalleryResponse = {
  results: ChatAttachment[];
  next_cursor: string | null;
};

/** Media gallery cursor params */
export type MediaGalleryCursorParams = {
  cursor?: string;
  page_size?: number;
};

/** Conversation list filter params */
export type ConversationListParams = {
  scope_type?: ScopeType;
  scope_id?: string;
  page?: number;
  page_size?: number;
};

/** Message search params */
export type MessageSearchParams = {
  q: string;
  conversation_id?: string;
  scope_type?: ScopeType;
  scope_id?: string;
  page?: number;
  page_size?: number;
};

// =============================================================================
// UNREAD COUNTS — bare dict from backend
// =============================================================================

/** UnreadCountsView returns { "global": 5, "business_<id>": 2, ... } */
export type UnreadCounts = Record<string, number>;

// =============================================================================
// WEBSOCKET EVENT TYPES
// =============================================================================

/** WebSocket connection states */
export type WsState = "connecting" | "connected" | "disconnected" | "reconnecting";

// --- Client → Server events (12 event types from consumers.py EVENT_HANDLERS) ---

export type WsMessageSendEvent = {
  type: "message.send";
  conversation_id: string;
  content: string;
  content_type?: MessageContentType;
  sender_type?: ParticipantType;
  sender_id?: string;
  attachment_ids?: string[];
};

export type WsMessageEditEvent = {
  type: "message.edit";
  conversation_id: string;
  message_id: string;
  content: string;
};

export type WsMessageDeleteEvent = {
  type: "message.delete";
  conversation_id: string;
  message_id: string;
};

export type WsTypingStartEvent = {
  type: "typing.start";
  conversation_id: string;
};

export type WsTypingStopEvent = {
  type: "typing.stop";
  conversation_id: string;
};

export type WsSeenEvent = {
  type: "seen";
  conversation_id: string;
  last_seen_message_id: string;
};

export type WsDeliveredEvent = {
  type: "delivered";
  conversation_id: string;
  last_delivered_message_id: string;
};

export type WsPresenceSubscribeEvent = {
  type: "presence.subscribe";
  user_ids: string[];
};

export type WsConversationJoinEvent = {
  type: "conversation.join";
  conversation_id: string;
};

export type WsConversationLeaveEvent = {
  type: "conversation.leave";
  conversation_id: string;
};

export type WsReactionAddEvent = {
  type: "reaction.add";
  conversation_id: string;
  message_id: string;
  reaction: ReactionType;
};

export type WsReactionRemoveEvent = {
  type: "reaction.remove";
  conversation_id: string;
  message_id: string;
  reaction: ReactionType;
};

export type WsClientEvent =
  | WsMessageSendEvent
  | WsMessageEditEvent
  | WsMessageDeleteEvent
  | WsTypingStartEvent
  | WsTypingStopEvent
  | WsSeenEvent
  | WsDeliveredEvent
  | WsPresenceSubscribeEvent
  | WsConversationJoinEvent
  | WsConversationLeaveEvent
  | WsReactionAddEvent
  | WsReactionRemoveEvent;

// --- Server → Client events (10 event types from consumers.py channel receivers) ---

/**
 * Backend sends flat fields (not nested under `message` key).
 * consumers.py `chat_message_new` does: { "type": "message.new", **event["payload"] }
 * Reactions/my_reactions are NOT included in WS payload — must init empty on cache insert.
 */
export type WsNewMessagePayload = {
  type: "message.new";
  id: string;
  conversation_id: string;
  sender_type: ParticipantType;
  sender_id: string;
  sender_name: string;
  sender_avatar_url: string | null;
  content_type: MessageContentType;
  content: string;
  status: MessageStatus;
  sequence_number: number;
  edited_at: string | null;
  created_at: string;
  attachments: ChatAttachment[];
};

export type WsMessageEditedPayload = {
  type: "message.edited";
  conversation_id: string;
  message_id: string;
  content: string;
  edited_at: string | null;
};

export type WsMessageDeletedPayload = {
  type: "message.deleted";
  conversation_id: string;
  message_id: string;
};

export type WsTypingPayload = {
  type: "typing";
  conversation_id: string;
  user_id: string;
  is_typing: boolean;
};

export type WsSeenUpdatePayload = {
  type: "seen.update";
  conversation_id: string;
  participant_id: string;
  last_seen_message_id: string;
};

export type WsDeliveredUpdatePayload = {
  type: "delivered.update";
  conversation_id: string;
  participant_id: string;
  last_delivered_message_id: string;
};

export type WsPresencePayload = {
  type: "presence";
  user_id: string;
  is_online: boolean;
};

export type WsReactionUpdatePayload = {
  type: "reaction.update";
  conversation_id: string;
  message_id: string;
  user_id: string;
  reaction: ReactionType;
  action: "added" | "removed";
};

export type WsConversationNewPayload = {
  type: "conversation.new";
  conversation_id: string;
  conversation_type: ConversationType;
  name: string;
  scope_type: ScopeType;
};

export type WsErrorPayload = {
  type: "error";
  message: string;
  code?: string;
};

export type WsServerEvent =
  | WsNewMessagePayload
  | WsMessageEditedPayload
  | WsMessageDeletedPayload
  | WsTypingPayload
  | WsSeenUpdatePayload
  | WsDeliveredUpdatePayload
  | WsPresencePayload
  | WsReactionUpdatePayload
  | WsConversationNewPayload
  | WsErrorPayload;
