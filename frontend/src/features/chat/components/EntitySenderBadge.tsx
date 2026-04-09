"use client";

import { Building2, Globe } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { ParticipantType } from "@/features/chat/types";

interface EntitySenderBadgeProps {
  participantType: ParticipantType;
  size?: "sm" | "md";
  className?: string;
}

/**
 * Small visual badge indicating entity type (business/platform)
 * on conversation list items in the entity inbox.
 */
export function EntitySenderBadge({
  participantType,
  size = "sm",
  className,
}: EntitySenderBadgeProps) {
  if (participantType === "user") return null;

  const Icon = participantType === "business" ? Building2 : Globe;
  const label =
    participantType === "business" ? "Business account" : "Platform account";

  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";
  const badgeSize =
    size === "sm" ? "h-4 w-4" : "h-5 w-5";

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            data-testid="entity-sender-badge"
            className={cn(
              "inline-flex items-center justify-center rounded-full bg-muted",
              badgeSize,
              className,
            )}
          >
            <Icon className={cn(iconSize, "text-muted-foreground")} />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
