"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useLeaveConversation } from "@/features/chat/hooks/use-chat-mutations";

interface LeaveConversationButtonProps {
  conversationId: string;
  onLeft?: () => void;
}

/**
 * Leave conversation button with confirmation dialog.
 */
export function LeaveConversationButton({
  conversationId,
  onLeft,
}: LeaveConversationButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const leave = useLeaveConversation();

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="text-destructive hover:text-destructive"
        onClick={() => setShowConfirm(true)}
        data-testid="leave-conversation-button"
      >
        <LogOut className="mr-1.5 h-3.5 w-3.5" />
        Leave conversation
      </Button>

      <ConfirmActionDialog
        open={showConfirm}
        onOpenChange={setShowConfirm}
        title="Leave conversation?"
        description="You will no longer receive messages from this conversation. This action cannot be undone."
        confirmLabel="Leave"
        variant="destructive"
        onConfirm={() => {
          leave.mutate(conversationId, {
            onSuccess: () => {
              setShowConfirm(false);
              onLeft?.();
            },
          });
        }}
        isLoading={leave.isPending}
      />
    </>
  );
}
