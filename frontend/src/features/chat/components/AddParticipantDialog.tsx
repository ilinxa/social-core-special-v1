"use client";

import { useCallback, useRef, useState } from "react";
import { Search, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAddParticipant } from "@/features/chat/hooks/use-chat-mutations";
import type { ChatParticipant } from "@/features/chat/types";

interface AddParticipantDialogProps {
  conversationId: string;
  existingParticipants: ChatParticipant[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog to search and add users to a group conversation.
 * Filters out users already in the conversation.
 *
 * Note: This uses a simple participant_id input approach.
 * A full user search integration would be added in Phase 5.
 */
export function AddParticipantDialog({
  conversationId,
  existingParticipants,
  open,
  onOpenChange,
}: AddParticipantDialogProps) {
  const [participantId, setParticipantId] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const addParticipant = useAddParticipant(conversationId);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) setParticipantId("");
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const handleAdd = useCallback(() => {
    const trimmedId = participantId.trim();
    if (!trimmedId) return;

    const activeIds = new Set(
      existingParticipants
        .filter((p) => p.is_active)
        .map((p) => p.participant_id),
    );

    if (activeIds.has(trimmedId)) {
      toast.error("This user is already a participant");
      return;
    }

    addParticipant.mutate(
      {
        participant_type: "user",
        participant_id: trimmedId,
      },
      {
        onSuccess: () => {
          toast.success("Participant added");
          setParticipantId("");
          onOpenChange(false);
        },
      },
    );
  }, [participantId, existingParticipants, addParticipant, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Add participant</DialogTitle>
          <DialogDescription>
            Add a user to this conversation by their ID.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              ref={inputRef}
              placeholder="Enter user ID..."
              value={participantId}
              onChange={(e) => setParticipantId(e.target.value)}
              className="pl-8"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAdd();
              }}
            />
          </div>

          <Button
            className="w-full"
            onClick={handleAdd}
            disabled={!participantId.trim() || addParticipant.isPending}
            data-testid="add-participant-submit"
          >
            <UserPlus className="mr-1.5 h-3.5 w-3.5" />
            Add to conversation
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
