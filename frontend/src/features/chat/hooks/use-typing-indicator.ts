"use client";

/**
 * Typing Indicator Hook
 * =====================
 * Manages sending typing.start/typing.stop events via WS.
 *
 * - On first keystroke: send typing.start
 * - After 3s of inactivity: send typing.stop
 * - Throttle typing.start to max 1 per 2s
 */

import { useCallback, useRef } from "react";

import type { WsClient } from "@/lib/ws-client";
import {
  TYPING_THROTTLE_MS,
  TYPING_TIMEOUT_MS,
} from "@/features/chat/constants/chat-constants";

export function useTypingIndicator(
  ws: WsClient | null,
  conversationId: string,
) {
  const isTypingRef = useRef(false);
  const lastSentRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sendTypingStart = useCallback(() => {
    if (!ws || ws.state !== "connected") return;

    const now = Date.now();
    if (now - lastSentRef.current < TYPING_THROTTLE_MS) return;

    ws.send({
      type: "typing.start",
      conversation_id: conversationId,
    });
    lastSentRef.current = now;
    isTypingRef.current = true;
  }, [ws, conversationId]);

  const sendTypingStop = useCallback(() => {
    if (!ws || ws.state !== "connected" || !isTypingRef.current) return;

    ws.send({
      type: "typing.stop",
      conversation_id: conversationId,
    });
    isTypingRef.current = false;
  }, [ws, conversationId]);

  /**
   * Call this on every keystroke in the compose input.
   * Handles throttling and auto-stop internally.
   */
  const onKeystroke = useCallback(() => {
    sendTypingStart();

    // Reset inactivity timer
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      sendTypingStop();
      timeoutRef.current = null;
    }, TYPING_TIMEOUT_MS);
  }, [sendTypingStart, sendTypingStop]);

  /**
   * Call this when the user sends a message or navigates away.
   * Immediately stops the typing indicator.
   */
  const stopTyping = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    sendTypingStop();
  }, [sendTypingStop]);

  return { onKeystroke, stopTyping };
}
