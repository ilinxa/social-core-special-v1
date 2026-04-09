"use client";

import { memo } from "react";
import { BellOff } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ConversationListItem as ConversationListItemType } from "@/features/chat/types";
import type { ParticipantType } from "@/features/chat/types";
import { EntitySenderBadge } from "./EntitySenderBadge";

interface ConversationListItemProps {
  conversation: ConversationListItemType;
  isActive: boolean;
  onClick: (id: string) => void;
  /** When shown in entity inbox, show the entity type badge */
  entityType?: ParticipantType;
}

export const ConversationListItem = memo(function ConversationListItem({
  conversation,
  isActive,
  onClick,
  entityType,
}: ConversationListItemProps) {
  const { id, name, last_message, unread_count, is_muted, conversation_type } =
    conversation;

  return (
    <button
      type="button"
      role="option"
      aria-selected={isActive}
      onClick={() => onClick(id)}
      className={cn(
        "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors",
        "hover:bg-accent/50",
        isActive && "bg-accent",
      )}
    >
      {/* Avatar */}
      <div className="relative">
        <Avatar>
          <AvatarFallback>
            {conversation_type === "group" ? "#" : name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        {entityType && (
          <div className="absolute -bottom-0.5 -right-0.5">
            <EntitySenderBadge participantType={entityType} size="sm" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "truncate text-sm",
              unread_count > 0 ? "font-semibold" : "font-medium",
            )}
          >
            {name}
          </span>
          {last_message && (
            <span className="shrink-0 text-xs text-muted-foreground">
              {formatTime(last_message.created_at)}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "truncate text-xs",
              unread_count > 0
                ? "font-medium text-foreground"
                : "text-muted-foreground",
            )}
          >
            {last_message
              ? `${last_message.sender_name}: ${last_message.content_preview}`
              : "No messages yet"}
          </span>
          <div className="flex shrink-0 items-center gap-1">
            {is_muted && (
              <BellOff className="h-3 w-3 text-muted-foreground" />
            )}
            {unread_count > 0 && (
              <Badge variant="default" className="h-5 min-w-5 px-1.5 text-xs">
                {unread_count > 99 ? "99+" : unread_count}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </button>
  );
});

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();

  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isToday) {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  }

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();

  if (isYesterday) return "Yesterday";

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
