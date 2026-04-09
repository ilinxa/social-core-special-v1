"use client";

/**
 * Chat WebSocket Hook
 * ====================
 * Central hook that bridges WsClient ↔ TQ cache + Zustand store.
 *
 * Handles all server→client events:
 * - message.new → insert into TQ cache, update conversation list
 * - message.edited → update message in TQ cache
 * - message.deleted → mark message deleted in TQ cache
 * - typing → update Zustand typing state
 * - seen.update → update Zustand watermarks
 * - delivered.update → update Zustand watermarks
 * - presence → update Zustand online users
 * - reaction.update → update message reactions in TQ cache
 * - conversation.new → invalidate conversation queries
 * - error → toast notification
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { WsClient } from "@/lib/ws-client";
import { getAccessToken } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import { useChatStore } from "@/stores/chat-store";
import { useUser } from "@/stores/auth-store";
import {
  TYPING_DISPLAY_TIMEOUT_MS,
} from "@/features/chat/constants/chat-constants";
import type {
  ChatMessage,
  ReactionType,
  WsNewMessagePayload,
  WsMessageEditedPayload,
  WsMessageDeletedPayload,
  WsTypingPayload,
  WsSeenUpdatePayload,
  WsDeliveredUpdatePayload,
  WsPresencePayload,
  WsReactionUpdatePayload,
  WsConversationNewPayload,
  WsErrorPayload,
} from "@/features/chat/types";
import {
  insertMessageInCache,
  updateMessageInCache,
  updateReactionInCache,
  moveConversationToTop,
  incrementConversationUnread,
} from "@/features/chat/utils/optimistic-updates";

const EMPTY_REACTIONS: Record<ReactionType, number> = {
  like: 0,
  heart: 0,
  laugh: 0,
  wow: 0,
  sad: 0,
  angry: 0,
};

/**
 * Build WS URL from the API base URL.
 * Converts http(s)://host:port → ws(s)://host:port/ws/chat/
 */
function buildWsUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const wsBase = apiUrl.replace(/^http/, "ws");
  return `${wsBase}/ws/chat/`;
}

/**
 * Main hook to manage the chat WebSocket connection.
 * Should be rendered once at the ChatLayout level.
 *
 * Returns the WsClient instance for sending events.
 */
export function useChatWs(): WsClient | null {
  const queryClient = useQueryClient();
  const user = useUser();
  const currentUserId = user?.id ?? "";

  const wsRef = useRef<WsClient | null>(null);
  const [wsClient, setWsClient] = useState<WsClient | null>(null);
  const typingTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const setWsState = useChatStore((s) => s.setWsState);
  const setTyping = useChatStore((s) => s.setTyping);
  const setOnline = useChatStore((s) => s.setOnline);
  const setSeenWatermark = useChatStore((s) => s.setSeenWatermark);
  const setDeliveredWatermark = useChatStore((s) => s.setDeliveredWatermark);
  const activeConversationId = useChatStore((s) => s.activeConversationId);
  const incrementUnread = useChatStore((s) => s.incrementUnread);

  // Ref to avoid stale closures in WS callbacks
  const activeConvIdRef = useRef(activeConversationId);
  useEffect(() => {
    activeConvIdRef.current = activeConversationId;
  }, [activeConversationId]);

  const currentUserIdRef = useRef(currentUserId);
  useEffect(() => {
    currentUserIdRef.current = currentUserId;
  }, [currentUserId]);

  // -------------------------------------------------------------------------
  // EVENT HANDLERS
  // -------------------------------------------------------------------------

  const handleNewMessage = useCallback(
    (payload: WsNewMessagePayload) => {
      // Backend sends flat fields (not nested under `message` key)
      // WS payload omits reactions/my_reactions — initialize empty
      const fullMessage: ChatMessage = {
        id: payload.id,
        conversation_id: payload.conversation_id,
        sender_type: payload.sender_type,
        sender_id: payload.sender_id,
        sender_name: payload.sender_name,
        sender_avatar_url: payload.sender_avatar_url,
        content_type: payload.content_type,
        content: payload.content,
        status: payload.status,
        sequence_number: payload.sequence_number,
        edited_at: payload.edited_at,
        created_at: payload.created_at,
        attachments: payload.attachments,
        reactions: { ...EMPTY_REACTIONS },
        my_reactions: [],
      };

      // Insert into TQ messages cache
      insertMessageInCache(queryClient, payload.conversation_id, fullMessage);

      // Update conversation list (move to top, update last_message)
      moveConversationToTop(queryClient, payload.conversation_id, {
        id: payload.id,
        sender_type: payload.sender_type,
        sender_id: payload.sender_id,
        sender_name: payload.sender_name,
        content_preview: payload.content.slice(0, 200),
        created_at: payload.created_at,
      });

      // If not the active conversation, increment unread
      if (
        payload.conversation_id !== activeConvIdRef.current &&
        payload.sender_id !== currentUserIdRef.current
      ) {
        incrementConversationUnread(queryClient, payload.conversation_id);
        incrementUnread(payload.conversation_id);
      }

      // Clear typing for this sender
      setTyping(payload.conversation_id, payload.sender_id, false);
    },
    [queryClient, incrementUnread, setTyping],
  );

  const handleMessageEdited = useCallback(
    (payload: WsMessageEditedPayload) => {
      updateMessageInCache(
        queryClient,
        payload.conversation_id,
        payload.message_id,
        {
          content: payload.content,
          edited_at: payload.edited_at,
          status: "edited",
        },
      );
    },
    [queryClient],
  );

  const handleMessageDeleted = useCallback(
    (payload: WsMessageDeletedPayload) => {
      updateMessageInCache(
        queryClient,
        payload.conversation_id,
        payload.message_id,
        { status: "deleted" },
      );
    },
    [queryClient],
  );

  const handleTyping = useCallback(
    (payload: WsTypingPayload) => {
      // Ignore own typing events
      if (payload.user_id === currentUserIdRef.current) return;

      setTyping(payload.conversation_id, payload.user_id, payload.is_typing);

      // Auto-clear typing after timeout
      if (payload.is_typing) {
        const timerKey = `${payload.conversation_id}:${payload.user_id}`;
        const existing = typingTimersRef.current.get(timerKey);
        if (existing) clearTimeout(existing);

        const timer = setTimeout(() => {
          setTyping(payload.conversation_id, payload.user_id, false);
          typingTimersRef.current.delete(timerKey);
        }, TYPING_DISPLAY_TIMEOUT_MS);

        typingTimersRef.current.set(timerKey, timer);
      }
    },
    [setTyping],
  );

  const handleSeenUpdate = useCallback(
    (payload: WsSeenUpdatePayload) => {
      setSeenWatermark(
        payload.conversation_id,
        payload.participant_id,
        payload.last_seen_message_id,
      );
    },
    [setSeenWatermark],
  );

  const handleDeliveredUpdate = useCallback(
    (payload: WsDeliveredUpdatePayload) => {
      setDeliveredWatermark(
        payload.conversation_id,
        payload.participant_id,
        payload.last_delivered_message_id,
      );
    },
    [setDeliveredWatermark],
  );

  const handlePresence = useCallback(
    (payload: WsPresencePayload) => {
      setOnline(payload.user_id, payload.is_online);
    },
    [setOnline],
  );

  const handleReactionUpdate = useCallback(
    (payload: WsReactionUpdatePayload) => {
      updateReactionInCache(
        queryClient,
        payload.conversation_id,
        payload.message_id,
        payload.reaction,
        payload.action,
        payload.user_id,
        currentUserIdRef.current,
      );
    },
    [queryClient],
  );

  const handleConversationNew = useCallback(
    (_payload: WsConversationNewPayload) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.chat.conversations(),
      });
    },
    [queryClient],
  );

  const handleError = useCallback((payload: WsErrorPayload) => {
    toast.error(payload.message || "Chat error");
  }, []);

  // -------------------------------------------------------------------------
  // CONNECTION LIFECYCLE
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!currentUserId) return;

    const ws = new WsClient({
      url: buildWsUrl(),
      getToken: getAccessToken,
      reconnect: true,
    });

    wsRef.current = ws;

    // Track connection state and expose ws client via subscription callback
    const unsubState = ws.onStateChange((state) => {
      setWsState(state);
      // Expose ws client to React tree from external subscription callback
      setWsClient(ws);
    });

    // Subscribe to server events
    const unsubs = [
      unsubState,
      ws.on<WsNewMessagePayload>("message.new", handleNewMessage),
      ws.on<WsMessageEditedPayload>("message.edited", handleMessageEdited),
      ws.on<WsMessageDeletedPayload>("message.deleted", handleMessageDeleted),
      ws.on<WsTypingPayload>("typing", handleTyping),
      ws.on<WsSeenUpdatePayload>("seen.update", handleSeenUpdate),
      ws.on<WsDeliveredUpdatePayload>("delivered.update", handleDeliveredUpdate),
      ws.on<WsPresencePayload>("presence", handlePresence),
      ws.on<WsReactionUpdatePayload>("reaction.update", handleReactionUpdate),
      ws.on<WsConversationNewPayload>("conversation.new", handleConversationNew),
      ws.on<WsErrorPayload>("error", handleError),
    ];

    ws.connect();

    // Copy ref for cleanup
    const timers = typingTimersRef.current;

    return () => {
      unsubs.forEach((unsub) => unsub());
      ws.disconnect();
      wsRef.current = null;

      // Clear all typing timers
      for (const timer of timers.values()) {
        clearTimeout(timer);
      }
      timers.clear();
    };
  }, [
    currentUserId,
    setWsState,
    handleNewMessage,
    handleMessageEdited,
    handleMessageDeleted,
    handleTyping,
    handleSeenUpdate,
    handleDeliveredUpdate,
    handlePresence,
    handleReactionUpdate,
    handleConversationNew,
    handleError,
  ]);

  return wsClient;
}
