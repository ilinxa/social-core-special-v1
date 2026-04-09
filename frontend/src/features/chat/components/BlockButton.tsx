"use client";

import { useState } from "react";
import { Ban } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useBlockParticipant } from "@/features/chat/hooks/use-chat-mutations";
import type { ParticipantType } from "@/features/chat/types";

interface BlockButtonProps {
  blockedType: ParticipantType;
  blockedId: string;
  blockedName: string;
}

/**
 * Block action from conversation header or participant actions.
 * Shows confirmation dialog before blocking.
 */
export function BlockButton({
  blockedType,
  blockedId,
  blockedName,
}: BlockButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const block = useBlockParticipant();

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="text-destructive hover:text-destructive"
        onClick={() => setShowConfirm(true)}
        data-testid="block-button"
      >
        <Ban className="mr-1.5 h-3.5 w-3.5" />
        Block
      </Button>

      <ConfirmActionDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        title={`Block ${blockedName}?`}
        description={`You will no longer receive messages from ${blockedName}. You can unblock them later.`}
        confirmLabel="Block"
        variant="destructive"
        onConfirm={() => {
          block.mutate({
            blocked_type: blockedType,
            blocked_id: blockedId,
          });
          setShowConfirm(false);
        }}
        isLoading={block.isPending}
      />
    </>
  );
}
