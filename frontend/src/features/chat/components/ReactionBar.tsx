"use client";

import { SmilePlus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { REACTION_EMOJI } from "@/features/chat/constants/chat-constants";
import {
  useAddReaction,
  useRemoveReaction,
} from "@/features/chat/hooks/use-chat-mutations";
import type { ReactionType } from "@/features/chat/types";
import { ReactionPicker } from "./ReactionPicker";

interface ReactionBarProps {
  conversationId: string;
  messageId: string;
  reactions: Record<ReactionType, number>;
  myReactions: ReactionType[];
}

/**
 * Displays reaction counts below a message.
 * User's own reactions are highlighted. Click to toggle.
 * Includes a + button to open the ReactionPicker.
 */
export function ReactionBar({
  conversationId,
  messageId,
  reactions,
  myReactions,
}: ReactionBarProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const addReaction = useAddReaction(conversationId);
  const removeReaction = useRemoveReaction(conversationId);

  const activeReactions = (
    Object.entries(reactions) as [ReactionType, number][]
  ).filter(([, count]) => count > 0);

  const handleToggle = (reaction: ReactionType) => {
    if (myReactions.includes(reaction)) {
      removeReaction.mutate({ messageId, reaction });
    } else {
      addReaction.mutate({ messageId, reaction });
    }
  };

  const handlePickerSelect = (reaction: ReactionType) => {
    if (!myReactions.includes(reaction)) {
      addReaction.mutate({ messageId, reaction });
    }
  };

  if (activeReactions.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-1" data-testid="reaction-bar">
      {activeReactions.map(([reaction, count]) => {
        const isOwn = myReactions.includes(reaction);
        return (
          <button
            key={reaction}
            onClick={() => handleToggle(reaction)}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-colors",
              isOwn
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border bg-muted hover:bg-accent",
            )}
            data-testid={`reaction-badge-${reaction}`}
          >
            <span>{REACTION_EMOJI[reaction]}</span>
            <span>{count}</span>
          </button>
        );
      })}

      <ReactionPicker
        trigger={
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6"
            data-testid="reaction-add-button"
          >
            <SmilePlus className="h-3 w-3" />
          </Button>
        }
        onSelect={handlePickerSelect}
        open={pickerOpen}
        onOpenChange={setPickerOpen}
      />
    </div>
  );
}
