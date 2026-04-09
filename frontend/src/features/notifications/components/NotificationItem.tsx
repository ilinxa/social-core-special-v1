"use client";

import React from "react";

import { Badge } from "@/components/ui/badge";
import { getNotificationMeta } from "@/features/notifications/constants/notification-constants";
import { NotificationTypeIcon } from "@/features/notifications/components/NotificationTypeIcon";
import type { NotificationLogItem } from "@/features/notifications/types";

// =============================================================================
// HELPERS
// =============================================================================

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return new Date(dateStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function getDynamicTitle(notification: NotificationLogItem): string {
  const meta = getNotificationMeta(notification.notification_type);
  const ctx = notification.context;

  // Dynamic titles from context when available
  if (notification.notification_type === "chat_message_received" && ctx.sender_name) {
    return `New message from ${ctx.sender_name}`;
  }
  if (notification.notification_type === "chat_request_received" && ctx.requester_name) {
    return `Chat request from ${ctx.requester_name}`;
  }
  if (notification.notification_type === "chat_group_added" && ctx.group_name) {
    return `Added to ${ctx.group_name}`;
  }
  if (notification.notification_type === "new_login" && ctx.device) {
    return `New login from ${ctx.device}`;
  }
  if (notification.notification_type === "promotions" && ctx.offer_title) {
    return `Special offer: ${ctx.offer_title}`;
  }

  return meta.title;
}

function getScopeBadgeLabel(
  scopeType: string,
  _scopeId: string | null,
): string | null {
  if (scopeType === "user") return null;
  if (scopeType === "platform") return "Platform";
  // Business scope — ideally resolve name from membership store,
  // but for now show "Business" as a fallback
  return "Business";
}

// =============================================================================
// COMPONENT
// =============================================================================

interface NotificationItemProps {
  notification: NotificationLogItem;
  compact?: boolean;
}

export const NotificationItem = React.memo(function NotificationItem({
  notification,
  compact = false,
}: NotificationItemProps) {
  const title = getDynamicTitle(notification);
  const timeStr = formatRelativeTime(notification.created_at);
  const scopeLabel = getScopeBadgeLabel(notification.scope_type, notification.scope_id);

  if (compact) {
    return (
      <div className="flex items-start gap-3 px-3 py-2.5 hover:bg-muted/50 transition-colors">
        <NotificationTypeIcon
          notificationType={notification.notification_type}
          className="mt-0.5 h-4 w-4 shrink-0"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm">{title}</p>
          <p className="text-xs text-muted-foreground">{timeStr}</p>
        </div>
        {scopeLabel && (
          <Badge variant="outline" className="shrink-0 text-[10px]">
            {scopeLabel}
          </Badge>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-start gap-4 rounded-lg border bg-card p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
        <NotificationTypeIcon
          notificationType={notification.notification_type}
          className="h-5 w-5"
        />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">{title}</p>
          {scopeLabel && (
            <Badge variant="secondary" className="text-[10px]">
              {scopeLabel}
            </Badge>
          )}
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">{timeStr}</p>
      </div>
    </div>
  );
});
