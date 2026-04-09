"use client";

import { MoreVertical, Shield, ShieldOff, UserMinus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  usePromoteParticipant,
  useRemoveParticipant,
  useDemoteParticipant,
} from "@/features/chat/hooks/use-chat-mutations";
import type { ChatParticipant, ConversationPermissions } from "@/features/chat/types";

interface ParticipantActionsProps {
  conversationId: string;
  participant: ChatParticipant;
  permissions: ConversationPermissions;
  currentUserId: string;
}

/**
 * Dropdown actions for a participant: promote, demote, remove.
 * Only shown for admins/managers with appropriate permissions.
 */
export function ParticipantActions({
  conversationId,
  participant,
  permissions,
  currentUserId,
}: ParticipantActionsProps) {
  const promote = usePromoteParticipant(conversationId);
  const demote = useDemoteParticipant(conversationId);
  const remove = useRemoveParticipant(conversationId);

  // Don't show actions for self or inactive participants
  if (
    participant.participant_id === currentUserId ||
    !participant.is_active
  ) {
    return null;
  }

  const canManage = permissions.can_manage_group;
  const canRemove = permissions.can_remove_participant;

  if (!canManage && !canRemove) return null;

  const isAdmin = participant.role === "admin";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-6 w-6"
          data-testid={`participant-actions-${participant.participant_id}`}
        >
          <MoreVertical className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {/* Promote/Demote */}
        {canManage && (
          <>
            {isAdmin ? (
              <DropdownMenuItem
                onClick={() => demote.mutate(participant.participant_id)}
              >
                <ShieldOff className="mr-2 h-3.5 w-3.5" />
                Remove admin
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem
                onClick={() => promote.mutate(participant.participant_id)}
              >
                <Shield className="mr-2 h-3.5 w-3.5" />
                Make admin
              </DropdownMenuItem>
            )}
          </>
        )}

        {/* Remove */}
        {canRemove && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() =>
                remove.mutate({
                  participantId: participant.participant_id,
                  participantType: participant.participant_type,
                })
              }
              className="text-destructive focus:text-destructive"
            >
              <UserMinus className="mr-2 h-3.5 w-3.5" />
              Remove from group
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
