"use client";

import { X, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

export type PendingAttachment = {
  id: string;
  file: File;
  previewUrl: string;
  uploading: boolean;
  uploadedId?: string;
  error?: string;
};

interface AttachmentPreviewProps {
  attachments: PendingAttachment[];
  onRemove: (id: string) => void;
}

/**
 * Thumbnail previews of pending image uploads before sending.
 * Shows upload progress indicator and remove button per image.
 */
export function AttachmentPreview({
  attachments,
  onRemove,
}: AttachmentPreviewProps) {
  if (attachments.length === 0) return null;

  return (
    <div
      className="flex gap-2 overflow-x-auto border-t px-4 py-2"
      data-testid="attachment-preview"
    >
      {attachments.map((att) => (
        <div
          key={att.id}
          className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg border"
        >
          <img
            src={att.previewUrl}
            alt={att.file.name}
            className="h-full w-full object-cover"
          />

          {/* Upload spinner overlay */}
          {att.uploading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40">
              <Loader2 className="h-4 w-4 animate-spin text-white" />
            </div>
          )}

          {/* Error overlay */}
          {att.error && (
            <div className="absolute inset-0 flex items-center justify-center bg-red-500/40">
              <span className="text-[10px] font-medium text-white">Error</span>
            </div>
          )}

          {/* Remove button */}
          <Button
            variant="ghost"
            size="icon-sm"
            className="absolute -right-1 -top-1 h-5 w-5 rounded-full bg-background shadow-sm"
            onClick={() => onRemove(att.id)}
            data-testid={`remove-attachment-${att.id}`}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ))}
    </div>
  );
}
