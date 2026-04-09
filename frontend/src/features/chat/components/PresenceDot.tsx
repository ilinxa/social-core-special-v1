"use client";

import { cn } from "@/lib/utils";
import { useIsUserOnline } from "@/stores/chat-store";

interface PresenceDotProps {
  userId: string;
  className?: string;
}

/**
 * Green/gray presence indicator dot.
 *
 * Reads from Zustand chat store (WS-driven presence data).
 */
export function PresenceDot({ userId, className }: PresenceDotProps) {
  const isOnline = useIsUserOnline(userId);

  return (
    <span
      className={cn(
        "block h-2.5 w-2.5 rounded-full border-2 border-background",
        isOnline ? "bg-green-500" : "bg-muted-foreground/40",
        className,
      )}
      aria-label={isOnline ? "Online" : "Offline"}
      data-testid="presence-dot"
      data-online={isOnline}
    />
  );
}
