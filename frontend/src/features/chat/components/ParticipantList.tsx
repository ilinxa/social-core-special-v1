"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { ChatParticipant, ConversationPermissions } from "@/features/chat/types";
import { PresenceDot } from "./PresenceDot";
import { ParticipantActions } from "./ParticipantActions";

interface ParticipantListProps {
  conversationId: string;
  participants: ChatParticipant[];
  permissions: ConversationPermissions;
  currentUserId: string;
}

/**
 * List of conversation participants with role badges and action menus.
 */
export function ParticipantList({
  conversationId,
  participants,
  permissions,
  currentUserId,
}: ParticipantListProps) {
  const activeParticipants = participants.filter((p) => p.is_active);
  const inactiveParticipants = participants.filter((p) => !p.is_active);

  return (
    <div className="space-y-1" data-testid="participant-list">
      <p className="px-3 text-xs font-medium text-muted-foreground">
        Members ({activeParticipants.length})
      </p>

      {activeParticipants.map((participant) => (
        <ParticipantRow
          key={participant.id}
          conversationId={conversationId}
          participant={participant}
          permissions={permissions}
          currentUserId={currentUserId}
        />
      ))}

      {inactiveParticipants.length > 0 && (
        <>
          <p className="px-3 pt-2 text-xs font-medium text-muted-foreground">
            Inactive ({inactiveParticipants.length})
          </p>
          {inactiveParticipants.map((participant) => (
            <ParticipantRow
              key={participant.id}
              conversationId={conversationId}
              participant={participant}
              permissions={permissions}
              currentUserId={currentUserId}
            />
          ))}
        </>
      )}
    </div>
  );
}

function ParticipantRow({
  conversationId,
  participant,
  permissions,
  currentUserId,
}: {
  conversationId: string;
  participant: ChatParticipant;
  permissions: ConversationPermissions;
  currentUserId: string;
}) {
  const isSelf = participant.participant_id === currentUserId;

  return (
    <div className="flex items-center gap-2 rounded-md px-3 py-1.5 hover:bg-accent">
      <div className="relative">
        <Avatar size="sm">
          {participant.avatar_url && (
            <AvatarImage src={participant.avatar_url} />
          )}
          <AvatarFallback>
            {participant.display_name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        {participant.participant_type === "user" && participant.is_active && (
          <PresenceDot
            userId={participant.participant_id}
            className="absolute -bottom-0.5 -right-0.5"
          />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm">
            {participant.display_name}
            {isSelf && (
              <span className="text-muted-foreground"> (you)</span>
            )}
          </span>
          {participant.role === "admin" && (
            <Badge variant="secondary" className="h-4 px-1 text-[10px]">
              Admin
            </Badge>
          )}
        </div>
        {!participant.is_active && (
          <p className="text-[10px] text-muted-foreground">Left</p>
        )}
      </div>

      <ParticipantActions
        conversationId={conversationId}
        participant={participant}
        permissions={permissions}
        currentUserId={currentUserId}
      />
    </div>
  );
}
