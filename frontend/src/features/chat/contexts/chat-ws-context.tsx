"use client";

/**
 * Chat WebSocket Context
 * ======================
 * Provides the WsClient instance to child components.
 * The ComposeBar needs it for typing indicators.
 */

import { createContext, useContext } from "react";

import type { WsClient } from "@/lib/ws-client";

const ChatWsContext = createContext<WsClient | null>(null);

export function ChatWsProvider({
  value,
  children,
}: {
  value: WsClient | null;
  children: React.ReactNode;
}) {
  return (
    <ChatWsContext.Provider value={value}>{children}</ChatWsContext.Provider>
  );
}

export function useChatWsClient(): WsClient | null {
  return useContext(ChatWsContext);
}
