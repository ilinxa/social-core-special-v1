"use client";

import { cn } from "@/lib/utils";
import type { ChatAttachment } from "@/features/chat/types";

interface AttachmentGridProps {
  attachments: ChatAttachment[];
  onImageClick?: (index: number) => void;
}

/**
 * Displays attachments in a responsive grid within a message bubble.
 * 1 image: full width. 2 images: side-by-side. 3-4: 2x2 grid.
 */
export function AttachmentGrid({ attachments, onImageClick }: AttachmentGridProps) {
  if (attachments.length === 0) return null;

  return (
    <div
      className={cn(
        "grid gap-1 overflow-hidden rounded-lg",
        attachments.length === 1 && "grid-cols-1",
        attachments.length === 2 && "grid-cols-2",
        attachments.length >= 3 && "grid-cols-2",
      )}
      data-testid="attachment-grid"
    >
      {attachments.slice(0, 4).map((attachment, index) => (
        <button
          key={attachment.id}
          type="button"
          className={cn(
            "relative overflow-hidden",
            attachments.length === 1 && "max-h-80",
            attachments.length >= 2 && "aspect-square",
          )}
          onClick={() => onImageClick?.(index)}
          data-testid={`attachment-${index}`}
        >
          <img
            src={attachment.url}
            alt={attachment.original_filename}
            className="h-full w-full object-cover"
            loading="lazy"
          />
          {/* Overlay for 4+ images showing remaining count */}
          {index === 3 && attachments.length > 4 && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50">
              <span className="text-lg font-bold text-white">
                +{attachments.length - 4}
              </span>
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
