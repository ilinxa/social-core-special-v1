"use client";

import { useCallback, useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Download, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ChatAttachment } from "@/features/chat/types";

interface ImageLightboxProps {
  attachments: ChatAttachment[];
  initialIndex: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Full-screen image viewer with navigation.
 * Uses shadcn Dialog for modal overlay.
 */
export function ImageLightbox({
  attachments,
  initialIndex,
  open,
  onOpenChange,
}: ImageLightboxProps) {
  // Use initialIndex directly, reset via key prop from parent
  const [currentIndex, setCurrentIndex] = useState(initialIndex);

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < attachments.length - 1;

  const goNext = useCallback(() => {
    if (hasNext) setCurrentIndex((i) => i + 1);
  }, [hasNext]);

  const goPrev = useCallback(() => {
    if (hasPrev) setCurrentIndex((i) => i - 1);
  }, [hasPrev]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "ArrowRight") goNext();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, goNext, goPrev]);

  const current = attachments[currentIndex];
  if (!current) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[90vw] border-none bg-black/90 p-0 sm:max-w-[90vw]"
        data-testid="image-lightbox"
      >
        <DialogTitle className="sr-only">
          Image {currentIndex + 1} of {attachments.length}
        </DialogTitle>

        {/* Close button */}
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-2 top-2 z-10 text-white hover:bg-white/20"
          onClick={() => onOpenChange(false)}
        >
          <X className="h-5 w-5" />
        </Button>

        {/* Download button */}
        <a
          href={current.url}
          download={current.original_filename}
          className="absolute right-12 top-2 z-10"
        >
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
          >
            <Download className="h-5 w-5" />
          </Button>
        </a>

        {/* Image */}
        <div className="flex min-h-[50vh] items-center justify-center p-8">
          <img
            src={current.url}
            alt={current.original_filename}
            className="max-h-[80vh] max-w-full object-contain"
          />
        </div>

        {/* Navigation */}
        {hasPrev && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-2 top-1/2 -translate-y-1/2 text-white hover:bg-white/20"
            onClick={goPrev}
          >
            <ChevronLeft className="h-6 w-6" />
          </Button>
        )}
        {hasNext && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-white hover:bg-white/20"
            onClick={goNext}
          >
            <ChevronRight className="h-6 w-6" />
          </Button>
        )}

        {/* Counter */}
        {attachments.length > 1 && (
          <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-white/80">
            {currentIndex + 1} / {attachments.length}
          </p>
        )}
      </DialogContent>
    </Dialog>
  );
}
