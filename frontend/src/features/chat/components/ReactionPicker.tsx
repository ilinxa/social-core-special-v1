"use client";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { REACTION_EMOJI } from "@/features/chat/constants/chat-constants";
import type { ReactionType } from "@/features/chat/types";

const REACTION_TYPES = Object.keys(REACTION_EMOJI) as ReactionType[];

interface ReactionPickerProps {
  onSelect: (reaction: ReactionType) => void;
  trigger: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Popover with 6 preset emoji buttons for adding reactions.
 */
export function ReactionPicker({
  onSelect,
  trigger,
  open,
  onOpenChange,
}: ReactionPickerProps) {
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>{trigger}</PopoverTrigger>
      <PopoverContent
        className="w-auto p-1"
        side="top"
        align="start"
        data-testid="reaction-picker"
      >
        <div className="flex gap-0.5">
          {REACTION_TYPES.map((reaction) => (
            <Button
              key={reaction}
              variant="ghost"
              size="icon-sm"
              className="h-8 w-8 text-base"
              onClick={() => {
                onSelect(reaction);
                onOpenChange?.(false);
              }}
              data-testid={`reaction-${reaction}`}
            >
              {REACTION_EMOJI[reaction]}
            </Button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
