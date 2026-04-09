"use client";

import { useState } from "react";
import { UserPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { Can } from "@/components/common/Can";
import type { ConversationDetailWithPerms } from "@/features/chat/types";
import { GroupInfoSection } from "./GroupInfoSection";
import { ParticipantList } from "./ParticipantList";
import { AddParticipantDialog } from "./AddParticipantDialog";
import { MuteToggle } from "./MuteToggle";
import { LeaveConversationButton } from "./LeaveConversationButton";
import { BlockList } from "./BlockList";

interface ConversationSettingsProps {
  conversation: ConversationDetailWithPerms;
  currentUserId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLeft?: () => void;
}

/**
 * Sheet/drawer for conversation settings.
 * Contains group info, participant list, mute toggle, leave button, and blocks.
 */
export function ConversationSettings({
  conversation,
  currentUserId,
  open,
  onOpenChange,
  onLeft,
}: ConversationSettingsProps) {
  const [showAddParticipant, setShowAddParticipant] = useState(false);
  const permissions = conversation._permissions;
  const isGroup = conversation.conversation_type === "group";

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-80 overflow-y-auto p-0">
          <SheetHeader className="border-b px-4 py-3">
            <SheetTitle className="text-sm">
              {isGroup ? "Group settings" : "Conversation settings"}
            </SheetTitle>
          </SheetHeader>

          <div className="space-y-4 py-4">
            {/* Group info */}
            {isGroup && (
              <>
                <GroupInfoSection
                  conversationId={conversation.id}
                  name={conversation.name}
                  description={conversation.description}
                  canEdit={permissions.can_edit_group}
                />
                <Separator />
              </>
            )}

            {/* Mute toggle */}
            <div className="px-3">
              <MuteToggle
                conversationId={conversation.id}
                isMuted={false}
              />
            </div>

            <Separator />

            {/* Participants */}
            {isGroup && (
              <>
                <div className="flex items-center justify-between px-3">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Participants
                  </p>
                  <Can allowed={permissions.can_add_participant}>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setShowAddParticipant(true)}
                      data-testid="add-participant-button"
                    >
                      <UserPlus className="h-3.5 w-3.5" />
                    </Button>
                  </Can>
                </div>
                <ParticipantList
                  conversationId={conversation.id}
                  participants={conversation.participants}
                  permissions={permissions}
                  currentUserId={currentUserId}
                />
                <Separator />
              </>
            )}

            {/* Blocked users */}
            <div className="px-3">
              <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                Blocked users
              </p>
              <BlockList />
            </div>

            <Separator />

            {/* Leave */}
            <Can allowed={permissions.can_leave}>
              <div className="px-3">
                <LeaveConversationButton
                  conversationId={conversation.id}
                  onLeft={onLeft}
                />
              </div>
            </Can>
          </div>
        </SheetContent>
      </Sheet>

      {isGroup && (
        <AddParticipantDialog
          conversationId={conversation.id}
          existingParticipants={conversation.participants}
          open={showAddParticipant}
          onOpenChange={setShowAddParticipant}
        />
      )}
    </>
  );
}
