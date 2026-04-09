"use client";

import { Check, CheckCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  useChatSeenWatermarks,
  useChatDeliveredWatermarks,
} from "@/stores/chat-store";

interface DeliveryStatusProps {
  conversationId: string;
  messageId: string;
  isOwn: boolean;
  isDm: boolean;
}

/**
 * Message delivery/read status indicator.
 *
 * DMs: ✓ (sent) → ✓✓ (delivered) → ✓✓ blue (seen)
 * Groups: "Seen by X" count instead of individual checkmarks.
 */
export function DeliveryStatus({
  conversationId,
  messageId,
  isOwn,
  isDm,
}: DeliveryStatusProps) {
  const seenWatermarks = useChatSeenWatermarks(conversationId);
  const deliveredWatermarks = useChatDeliveredWatermarks(conversationId);

  // Only show for own messages
  if (!isOwn) return null;

  if (isDm) {
    return (
      <DmDeliveryStatus
        messageId={messageId}
        seenWatermarks={seenWatermarks}
        deliveredWatermarks={deliveredWatermarks}
      />
    );
  }

  return (
    <GroupDeliveryStatus
      messageId={messageId}
      seenWatermarks={seenWatermarks}
    />
  );
}

function DmDeliveryStatus({
  messageId,
  seenWatermarks,
  deliveredWatermarks,
}: {
  messageId: string;
  seenWatermarks: Record<string, string>;
  deliveredWatermarks: Record<string, string>;
}) {
  // Check if the other participant has seen this message
  const isSeen = Object.values(seenWatermarks).some(
    (lastSeen) => lastSeen === messageId || lastSeen > messageId,
  );

  const isDelivered =
    isSeen ||
    Object.values(deliveredWatermarks).some(
      (lastDelivered) =>
        lastDelivered === messageId || lastDelivered > messageId,
    );

  if (isSeen) {
    return (
      <CheckCheck
        className="h-3.5 w-3.5 text-blue-500"
        aria-label="Seen"
        data-testid="delivery-seen"
      />
    );
  }

  if (isDelivered) {
    return (
      <CheckCheck
        className="h-3.5 w-3.5 text-muted-foreground"
        aria-label="Delivered"
        data-testid="delivery-delivered"
      />
    );
  }

  return (
    <Check
      className="h-3.5 w-3.5 text-muted-foreground"
      aria-label="Sent"
      data-testid="delivery-sent"
    />
  );
}

function GroupDeliveryStatus({
  messageId,
  seenWatermarks,
}: {
  messageId: string;
  seenWatermarks: Record<string, string>;
}) {
  const seenCount = Object.values(seenWatermarks).filter(
    (lastSeen) => lastSeen === messageId || lastSeen > messageId,
  ).length;

  if (seenCount === 0) {
    return (
      <Check
        className="h-3.5 w-3.5 text-muted-foreground"
        aria-label="Sent"
        data-testid="delivery-sent"
      />
    );
  }

  return (
    <span
      className={cn("text-xs", seenCount > 0 && "text-blue-500")}
      data-testid="delivery-seen-count"
    >
      Seen by {seenCount}
    </span>
  );
}
