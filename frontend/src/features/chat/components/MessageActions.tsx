"use client";

import { useState } from "react";
import { Copy, Edit, MoreVertical, SmilePlus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CHAT_EDIT_WINDOW_MINUTES } from "@/features/chat/constants/chat-constants";
import type { ChatMessage, ReactionType, ConversationPermissions } from "@/features/chat/types";
import { ReactionPicker } from "./ReactionPicker";

interface MessageActionsProps {
  message: ChatMessage;
  isOwn: boolean;
  permissions: ConversationPermissions;
  onEdit: () => void;
  onDelete: () => void;
  onReact: (reaction: ReactionType) => void;
}

/**
 * Context menu for message actions: edit, delete, react, copy.
 * Actions are permission-gated and time-restricted (edit within 15min).
 */
export function MessageActions({
  message,
  isOwn,
  permissions,
  onEdit,
  onDelete,
  onReact,
}: MessageActionsProps) {
  const [pickerOpen, setPickerOpen] = useState(false);

  const canEdit =
    isOwn &&
    message.content_type === "text" &&
    message.status !== "deleted" &&
    isWithinEditWindow(message.created_at);

  const canDelete =
    (isOwn || permissions.can_manage_group) &&
    message.status !== "deleted";

  const canReact = permissions.can_send_message;

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      toast.success("Message copied");
    });
  };

  return (
    <div
      className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100"
      data-testid="message-actions"
    >
      {/* Quick reaction button */}
      {canReact && (
        <ReactionPicker
          trigger={
            <Button variant="ghost" size="icon-sm" className="h-6 w-6">
              <SmilePlus className="h-3 w-3" />
            </Button>
          }
          onSelect={onReact}
          open={pickerOpen}
          onOpenChange={setPickerOpen}
        />
      )}

      {/* More actions dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6"
            data-testid="message-actions-trigger"
          >
            <MoreVertical className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          {/* Copy */}
          {message.content_type === "text" && message.status !== "deleted" && (
            <DropdownMenuItem onClick={handleCopy}>
              <Copy className="mr-2 h-3.5 w-3.5" />
              Copy text
            </DropdownMenuItem>
          )}

          {/* Edit */}
          {canEdit && (
            <DropdownMenuItem onClick={onEdit}>
              <Edit className="mr-2 h-3.5 w-3.5" />
              Edit
            </DropdownMenuItem>
          )}

          {/* Delete */}
          {canDelete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={onDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-3.5 w-3.5" />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function isWithinEditWindow(createdAt: string): boolean {
  const created = new Date(createdAt).getTime();
  const now = Date.now();
  return now - created < CHAT_EDIT_WINDOW_MINUTES * 60 * 1000;
}
