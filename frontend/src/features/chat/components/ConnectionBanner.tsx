"use client";

import { Wifi, WifiOff } from "lucide-react";

import { cn } from "@/lib/utils";
import { useChatWsState } from "@/stores/chat-store";

/**
 * Banner showing WebSocket connection state.
 *
 * - Connected: hidden
 * - Connecting: "Connecting..."
 * - Reconnecting: "Reconnecting..."
 * - Disconnected: "Offline — messages may be delayed"
 */
export function ConnectionBanner() {
  const wsState = useChatWsState();

  if (wsState === "connected") return null;

  const config = BANNER_CONFIG[wsState];

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-2 px-4 py-1.5 text-xs font-medium",
        config.bg,
      )}
      role="status"
      aria-live="polite"
      data-testid="connection-banner"
    >
      <config.Icon className="h-3.5 w-3.5" />
      <span>{config.text}</span>
    </div>
  );
}

const BANNER_CONFIG = {
  connecting: {
    text: "Connecting...",
    bg: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200",
    Icon: Wifi,
  },
  reconnecting: {
    text: "Reconnecting...",
    bg: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200",
    Icon: Wifi,
  },
  disconnected: {
    text: "Offline — messages may be delayed",
    bg: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200",
    Icon: WifiOff,
  },
} as const;
