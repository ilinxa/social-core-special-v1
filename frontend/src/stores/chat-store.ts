"use client";

/**
 * Chat Zustand Store
 * ==================
 * App-wide ephemeral state for the chat system.
 *
 * Located in src/stores/ (NOT src/features/chat/) because nav badge
 * needs unread counts outside the chat feature.
 *
 * Stores ONLY client-side ephemeral state. Server data (conversations,
 * messages, participants) stays in TanStack Query cache.
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";

import type { WsState } from "@/lib/ws-client";

// =============================================================================
// UPLOAD PROGRESS
// =============================================================================

export interface UploadProgress {
  id: string;
  filename: string;
  progress: number; // 0-100
  status: "uploading" | "done" | "error";
  attachmentId?: string; // set when upload completes
}

// =============================================================================
// STATE & ACTIONS
// =============================================================================

interface ChatState {
  activeConversationId: string | null;
  wsState: WsState;
  typingUsers: Record<string, string[]>; // conversationId → [userId, ...]
  onlineUsers: Set<string>;
  drafts: Record<string, string>; // conversationId → draft text
  pendingUploads: Record<string, UploadProgress[]>; // conversationId → uploads
  unreadCounts: Record<string, number>; // scope key → count
  seenWatermarks: Record<string, Record<string, string>>; // convId → { participantId → lastSeenMsgId }
  deliveredWatermarks: Record<string, Record<string, string>>; // convId → { participantId → lastDeliveredMsgId }
}

interface ChatActions {
  setActiveConversation: (id: string | null) => void;
  setWsState: (state: WsState) => void;

  // Typing
  setTyping: (conversationId: string, userId: string, isTyping: boolean) => void;
  clearTyping: (conversationId: string) => void;

  // Presence
  setOnline: (userId: string, isOnline: boolean) => void;

  // Drafts
  setDraft: (conversationId: string, text: string) => void;
  clearDraft: (conversationId: string) => void;

  // Uploads
  setPendingUploads: (conversationId: string, uploads: UploadProgress[]) => void;
  clearPendingUploads: (conversationId: string) => void;

  // Unread
  setUnreadCounts: (counts: Record<string, number>) => void;
  incrementUnread: (scopeKey: string) => void;
  clearUnread: (scopeKey: string) => void;

  // Watermarks
  setSeenWatermark: (conversationId: string, participantId: string, messageId: string) => void;
  setDeliveredWatermark: (conversationId: string, participantId: string, messageId: string) => void;

  // Reset
  reset: () => void;
}

type ChatStore = ChatState & ChatActions;

const initialState: ChatState = {
  activeConversationId: null,
  wsState: "disconnected",
  typingUsers: {},
  onlineUsers: new Set<string>(),
  drafts: {},
  pendingUploads: {},
  unreadCounts: {},
  seenWatermarks: {},
  deliveredWatermarks: {},
};

// =============================================================================
// STORE
// =============================================================================

export const useChatStore = create<ChatStore>()(
  devtools(
    (set) => ({
      ...initialState,

      setActiveConversation: (id) =>
        set({ activeConversationId: id }, false, "chat/setActiveConversation"),

      setWsState: (wsState) =>
        set({ wsState }, false, "chat/setWsState"),

      // --- Typing ---
      setTyping: (conversationId, userId, isTyping) =>
        set(
          (state) => {
            const current = state.typingUsers[conversationId] ?? [];
            const filtered = current.filter((id) => id !== userId);
            const next = isTyping ? [...filtered, userId] : filtered;
            return {
              typingUsers: {
                ...state.typingUsers,
                [conversationId]: next,
              },
            };
          },
          false,
          "chat/setTyping",
        ),

      clearTyping: (conversationId) =>
        set(
          (state) => {
            const { [conversationId]: _, ...rest } = state.typingUsers;
            return { typingUsers: rest };
          },
          false,
          "chat/clearTyping",
        ),

      // --- Presence ---
      setOnline: (userId, isOnline) =>
        set(
          (state) => {
            const next = new Set(state.onlineUsers);
            if (isOnline) {
              next.add(userId);
            } else {
              next.delete(userId);
            }
            return { onlineUsers: next };
          },
          false,
          "chat/setOnline",
        ),

      // --- Drafts ---
      setDraft: (conversationId, text) =>
        set(
          (state) => ({
            drafts: { ...state.drafts, [conversationId]: text },
          }),
          false,
          "chat/setDraft",
        ),

      clearDraft: (conversationId) =>
        set(
          (state) => {
            const { [conversationId]: _, ...rest } = state.drafts;
            return { drafts: rest };
          },
          false,
          "chat/clearDraft",
        ),

      // --- Uploads ---
      setPendingUploads: (conversationId, uploads) =>
        set(
          (state) => ({
            pendingUploads: { ...state.pendingUploads, [conversationId]: uploads },
          }),
          false,
          "chat/setPendingUploads",
        ),

      clearPendingUploads: (conversationId) =>
        set(
          (state) => {
            const { [conversationId]: _, ...rest } = state.pendingUploads;
            return { pendingUploads: rest };
          },
          false,
          "chat/clearPendingUploads",
        ),

      // --- Unread ---
      setUnreadCounts: (counts) =>
        set({ unreadCounts: counts }, false, "chat/setUnreadCounts"),

      incrementUnread: (scopeKey) =>
        set(
          (state) => ({
            unreadCounts: {
              ...state.unreadCounts,
              [scopeKey]: (state.unreadCounts[scopeKey] ?? 0) + 1,
            },
          }),
          false,
          "chat/incrementUnread",
        ),

      clearUnread: (scopeKey) =>
        set(
          (state) => {
            const { [scopeKey]: _, ...rest } = state.unreadCounts;
            return { unreadCounts: rest };
          },
          false,
          "chat/clearUnread",
        ),

      // --- Watermarks ---
      setSeenWatermark: (conversationId, participantId, messageId) =>
        set(
          (state) => ({
            seenWatermarks: {
              ...state.seenWatermarks,
              [conversationId]: {
                ...state.seenWatermarks[conversationId],
                [participantId]: messageId,
              },
            },
          }),
          false,
          "chat/setSeenWatermark",
        ),

      setDeliveredWatermark: (conversationId, participantId, messageId) =>
        set(
          (state) => ({
            deliveredWatermarks: {
              ...state.deliveredWatermarks,
              [conversationId]: {
                ...state.deliveredWatermarks[conversationId],
                [participantId]: messageId,
              },
            },
          }),
          false,
          "chat/setDeliveredWatermark",
        ),

      // --- Reset ---
      reset: () => set(initialState, false, "chat/reset"),
    }),
    { name: "chat-store" },
  ),
);

// =============================================================================
// SELECTOR HOOKS
// =============================================================================

export function useChatActiveConversation(): string | null {
  return useChatStore((s) => s.activeConversationId);
}

export function useChatWsState(): WsState {
  return useChatStore((s) => s.wsState);
}

export function useChatTypingUsers(conversationId: string): string[] {
  return useChatStore(
    useShallow((s) => s.typingUsers[conversationId] ?? []),
  );
}

export function useChatOnlineUsers(): Set<string> {
  return useChatStore((s) => s.onlineUsers);
}

export function useIsUserOnline(userId: string): boolean {
  return useChatStore((s) => s.onlineUsers.has(userId));
}

export function useChatDraft(conversationId: string): string {
  return useChatStore((s) => s.drafts[conversationId] ?? "");
}

export function useChatPendingUploads(conversationId: string): UploadProgress[] {
  return useChatStore(
    useShallow((s) => s.pendingUploads[conversationId] ?? []),
  );
}

export function useChatUnreadCounts(): Record<string, number> {
  return useChatStore(useShallow((s) => s.unreadCounts));
}

export function useChatTotalUnread(): number {
  return useChatStore((s) =>
    Object.values(s.unreadCounts).reduce((sum, n) => sum + n, 0),
  );
}

export function useChatSeenWatermarks(
  conversationId: string,
): Record<string, string> {
  return useChatStore(
    useShallow((s) => s.seenWatermarks[conversationId] ?? {}),
  );
}

export function useChatDeliveredWatermarks(
  conversationId: string,
): Record<string, string> {
  return useChatStore(
    useShallow((s) => s.deliveredWatermarks[conversationId] ?? {}),
  );
}

// =============================================================================
// NON-REACT ACCESS (for WS handler, API layer)
// =============================================================================

export function getChatStore() {
  return useChatStore.getState();
}
