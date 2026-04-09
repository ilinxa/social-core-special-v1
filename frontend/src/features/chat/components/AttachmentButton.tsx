"use client";

import { useRef } from "react";
import { Paperclip } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  CHAT_ALLOWED_IMAGE_TYPES,
  CHAT_MAX_IMAGE_SIZE,
  CHAT_MAX_ATTACHMENTS,
} from "@/features/chat/constants/chat-constants";

interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  currentCount: number;
  disabled?: boolean;
}

/**
 * File input trigger for adding image attachments to a message.
 * Validates file type and size client-side before calling onFilesSelected.
 */
export function AttachmentButton({
  onFilesSelected,
  currentCount,
  disabled = false,
}: AttachmentButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;

    // Reset input so the same file can be selected again
    e.target.value = "";

    // Validate count
    const remaining = CHAT_MAX_ATTACHMENTS - currentCount;
    if (remaining <= 0) {
      toast.error(`Maximum ${CHAT_MAX_ATTACHMENTS} attachments allowed`);
      return;
    }

    const validFiles: File[] = [];

    for (const file of files.slice(0, remaining)) {
      // Validate type
      if (
        !CHAT_ALLOWED_IMAGE_TYPES.includes(
          file.type as (typeof CHAT_ALLOWED_IMAGE_TYPES)[number],
        )
      ) {
        toast.error(`${file.name}: Unsupported file type. Use JPEG, PNG, GIF, or WebP.`);
        continue;
      }

      // Validate size
      if (file.size > CHAT_MAX_IMAGE_SIZE) {
        toast.error(`${file.name}: File too large. Maximum 10 MB.`);
        continue;
      }

      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={CHAT_ALLOWED_IMAGE_TYPES.join(",")}
        multiple
        onChange={handleChange}
        className="hidden"
        data-testid="attachment-file-input"
      />
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={handleClick}
        disabled={disabled || currentCount >= CHAT_MAX_ATTACHMENTS}
        data-testid="attachment-button"
      >
        <Paperclip className="h-4 w-4" />
      </Button>
    </>
  );
}
