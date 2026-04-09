"use client";

import { useCallback, useRef, useState } from "react";
import { Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CHAT_MESSAGE_MAX_LENGTH } from "@/features/chat/constants/chat-constants";
import { useEditMessage } from "@/features/chat/hooks/use-chat-mutations";

interface EditMessageModeProps {
  conversationId: string;
  messageId: string;
  initialContent: string;
  onCancel: () => void;
  onComplete: () => void;
}

/**
 * Replaces the compose bar when editing a message.
 * Shows "Editing message" banner with cancel button, and save/cancel actions.
 */
export function EditMessageMode({
  conversationId,
  messageId,
  initialContent,
  onCancel,
  onComplete,
}: EditMessageModeProps) {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editMessage = useEditMessage(conversationId);

  const handleSave = useCallback(async () => {
    const trimmed = content.trim();
    if (!trimmed || trimmed === initialContent.trim() || isSaving) return;

    setIsSaving(true);
    try {
      await editMessage.mutateAsync({
        messageId,
        data: { content: trimmed },
      });
      onComplete();
    } finally {
      setIsSaving(false);
    }
  }, [content, initialContent, isSaving, editMessage, messageId, onComplete]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSave();
      }
      if (e.key === "Escape") {
        onCancel();
      }
    },
    [handleSave, onCancel],
  );

  return (
    <div className="border-t bg-background" data-testid="edit-message-mode">
      {/* Editing banner */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-1.5">
        <span className="text-xs font-medium text-muted-foreground">
          Editing message
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-5 w-5"
          onClick={onCancel}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>

      {/* Edit input */}
      <div className="flex items-end gap-2 px-4 py-3">
        <Textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => {
            if (e.target.value.length <= CHAT_MESSAGE_MAX_LENGTH) {
              setContent(e.target.value);
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={isSaving}
          className="min-h-[40px] max-h-[120px] resize-none text-sm"
          rows={1}
          autoFocus
        />
        <div className="flex gap-1">
          <Button
            size="icon"
            variant="ghost"
            onClick={onCancel}
            disabled={isSaving}
          >
            <X className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            onClick={handleSave}
            disabled={
              !content.trim() ||
              content.trim() === initialContent.trim() ||
              isSaving
            }
          >
            <Check className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
