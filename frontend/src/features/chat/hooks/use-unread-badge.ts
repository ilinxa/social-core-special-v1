"use client";

/**
 * Unread Badge Hook
 * =================
 * Returns unread count for nav badge display.
 *
 * Primary source: Zustand store (WS-updated).
 * Fallback: REST poll via useUnreadCounts() when WS is disconnected.
 */

import { useEffect } from "react";

import { useChatStore } from "@/stores/chat-store";
import { useUnreadCounts } from "@/features/chat/hooks/use-chat-queries";

/**
 * Returns total unread count across all scopes.
 * Syncs REST-fetched counts into Zustand store as fallback.
 */
export function useUnreadBadge(): number {
  const wsState = useChatStore((s) => s.wsState);
  const storeTotal = useChatStore((s) =>
    Object.values(s.unreadCounts).reduce((sum, n) => sum + n, 0),
  );
  const setUnreadCounts = useChatStore((s) => s.setUnreadCounts);

  // REST fallback — only enabled when WS is not connected
  const { data: restCounts } = useUnreadCounts();

  // Sync REST data into store when WS is disconnected
  useEffect(() => {
    if (wsState !== "connected" && restCounts) {
      setUnreadCounts(restCounts);
    }
  }, [wsState, restCounts, setUnreadCounts]);

  return storeTotal;
}

/**
 * Returns unread count for a specific scope key.
 */
export function useScopeUnreadBadge(scopeKey: string): number {
  return useChatStore((s) => s.unreadCounts[scopeKey] ?? 0);
}
