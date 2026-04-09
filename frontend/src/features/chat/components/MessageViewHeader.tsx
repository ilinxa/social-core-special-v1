"use client";

import { ArrowLeft, Hash, Search, Settings, Users } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import type { ConversationDetailWithPerms } from "@/features/chat/types";

interface MessageViewHeaderProps {
  conversation: ConversationDetailWithPerms;
  onBack: () => void;
  onOpenSettings?: () => void;
  onOpenSearch?: () => void;
}

export function MessageViewHeader({
  conversation,
  onBack,
  onOpenSettings,
  onOpenSearch,
}: MessageViewHeaderProps) {
  const participantCount = conversation.participants.filter(
    (p) => p.is_active,
  ).length;
  const isGroup = conversation.conversation_type === "group";

  return (
    <div className="flex items-center gap-3 border-b px-3 py-2">
      {/* Back button (mobile only) */}
      <Button
        variant="ghost"
        size="icon-sm"
        className="md:hidden"
        onClick={onBack}
      >
        <ArrowLeft className="h-4 w-4" />
      </Button>

      {/* Avatar */}
      <Avatar size="sm">
        <AvatarFallback>
          {isGroup ? <Hash className="h-3 w-3" /> : conversation.name.charAt(0).toUpperCase()}
        </AvatarFallback>
      </Avatar>

      {/* Name + participant count */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{conversation.name}</p>
        {isGroup && (
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Users className="h-3 w-3" />
            {participantCount} {participantCount === 1 ? "member" : "members"}
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1">
        {onOpenSearch && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onOpenSearch}
            data-testid="search-messages-button"
          >
            <Search className="h-4 w-4" />
          </Button>
        )}
        {onOpenSettings && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onOpenSettings}
            data-testid="conversation-settings-button"
          >
            <Settings className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
