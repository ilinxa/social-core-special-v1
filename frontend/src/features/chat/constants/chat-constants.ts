/**
 * Chat Constants
 * ==============
 * Frontend mirrors of backend chat constants.
 *
 * Backend source: apps.chat.constants
 */

import type { ReactionType } from "@/features/chat/types";

// =============================================================================
// REACTION EMOJI MAPPING
// =============================================================================

export const REACTION_EMOJI: Record<ReactionType, string> = {
  like: "\uD83D\uDC4D",
  heart: "\u2764\uFE0F",
  laugh: "\uD83D\uDE02",
  wow: "\uD83D\uDE2E",
  sad: "\uD83D\uDE22",
  angry: "\uD83D\uDE21",
};

// =============================================================================
// MESSAGE LIMITS
// =============================================================================

export const CHAT_MESSAGE_MAX_LENGTH = 5000;
export const CHAT_EDIT_WINDOW_MINUTES = 15;
export const CHAT_MESSAGE_PREVIEW_LENGTH = 200;
export const CHAT_REQUEST_MAX_MESSAGES = 3;

// =============================================================================
// GROUP LIMITS
// =============================================================================

export const CHAT_GROUP_MAX_PARTICIPANTS = 100;

// =============================================================================
// ATTACHMENT LIMITS
// =============================================================================

export const CHAT_MAX_ATTACHMENTS = 10;
export const CHAT_MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10 MB
export const CHAT_ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
] as const;

// =============================================================================
// WEBSOCKET
// =============================================================================

export const WS_HEARTBEAT_INTERVAL_MS = 20_000;
export const WS_PRESENCE_TTL_MS = 30_000;
export const WS_MAX_PRESENCE_SUBSCRIPTIONS = 50;

// =============================================================================
// TYPING INDICATOR
// =============================================================================

export const TYPING_THROTTLE_MS = 2_000;
export const TYPING_TIMEOUT_MS = 3_000;
export const TYPING_DISPLAY_TIMEOUT_MS = 5_000;

// =============================================================================
// PAGINATION DEFAULTS
// =============================================================================

export const DEFAULT_PAGE_SIZE = 20;
export const MESSAGES_PAGE_SIZE = 50;
export const MEDIA_GALLERY_PAGE_SIZE = 50;
