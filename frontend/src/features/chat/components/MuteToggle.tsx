"use client";

import { Bell, BellOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  useMuteConversation,
  useUnmuteConversation,
} from "@/features/chat/hooks/use-chat-mutations";

interface MuteToggleProps {
  conversationId: string;
  isMuted: boolean;
}

/**
 * Toggle button for muting/unmuting a conversation.
 */
export function MuteToggle({ conversationId, isMuted }: MuteToggleProps) {
  const mute = useMuteConversation();
  const unmute = useUnmuteConversation();
  const isPending = mute.isPending || unmute.isPending;

  const handleToggle = () => {
    if (isMuted) {
      unmute.mutate(conversationId);
    } else {
      mute.mutate(conversationId);
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleToggle}
      disabled={isPending}
      data-testid="mute-toggle"
    >
      {isMuted ? (
        <>
          <Bell className="mr-1.5 h-3.5 w-3.5" />
          Unmute
        </>
      ) : (
        <>
          <BellOff className="mr-1.5 h-3.5 w-3.5" />
          Mute
        </>
      )}
    </Button>
  );
}
