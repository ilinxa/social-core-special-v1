/**
 * DropZone
 * =========
 * HTML5 drag-and-drop wrapper for file uploads.
 * Visual feedback on drag-over, accessible status announcements.
 */

"use client";

import { useCallback, useState } from "react";
import { Upload } from "lucide-react";

import { cn } from "@/lib/utils";

type DropZoneProps = {
  onDrop: (files: FileList) => void;
  children: React.ReactNode;
  disabled?: boolean;
  accept?: string;
  className?: string;
};

export function DropZone({
  onDrop,
  children,
  disabled = false,
  className,
}: DropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragOver(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      if (disabled) return;
      if (e.dataTransfer.files.length > 0) {
        onDrop(e.dataTransfer.files);
      }
    },
    [disabled, onDrop],
  );

  return (
    <div
      className={cn("relative", className)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {children}

      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center rounded-lg border-2 border-dashed border-primary bg-primary/5">
          <div className="flex flex-col items-center gap-2 text-primary" aria-live="polite">
            <Upload className="h-8 w-8" />
            <p className="text-sm font-medium">Drop file to upload</p>
          </div>
        </div>
      )}
    </div>
  );
}
