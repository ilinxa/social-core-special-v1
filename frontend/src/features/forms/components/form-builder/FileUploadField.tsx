"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, ImagePlus, Trash2, FileIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// =============================================================================
// CONSTANTS
// =============================================================================

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
const DEFAULT_MAX_SIZE = 10 * 1024 * 1024; // 10 MB

// =============================================================================
// TYPES
// =============================================================================

interface FileUploadFieldProps {
  /** "file" or "image" */
  variant: "file" | "image";
  value: File | string | null;
  onChange: (value: File | null) => void;
  disabled?: boolean;
  /** From field.validation_rules */
  maxSize?: number;
  allowedTypes?: string[];
}

// =============================================================================
// COMPONENT
// =============================================================================

export function FileUploadField({
  variant,
  value,
  onChange,
  disabled,
  maxSize = DEFAULT_MAX_SIZE,
  allowedTypes,
}: FileUploadFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const isImage = variant === "image";
  const acceptTypes = isImage
    ? IMAGE_TYPES.join(",")
    : allowedTypes?.join(",") ?? undefined;

  // Create/cleanup preview URL for File objects
  useEffect(() => {
    if (!(value instanceof File)) {
      setPreviewUrl(null);
      return;
    }
    if (isImage || value.type.startsWith("image/")) {
      const url = URL.createObjectURL(value);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [value, isImage]);

  const displayUrl = previewUrl ?? (typeof value === "string" ? value : null);
  const hasFile = !!value;
  const fileName = value instanceof File ? value.name : typeof value === "string" ? value.split("/").pop() : null;

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      // Size check
      if (file.size > maxSize) {
        toast.error(`File must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`);
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      // Image type check
      if (isImage && !file.type.startsWith("image/")) {
        toast.error("Please select an image file (JPEG, PNG, GIF, or WebP)");
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      // Custom type check
      if (allowedTypes && !allowedTypes.includes(file.type)) {
        toast.error(`File type ${file.type} is not allowed`);
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      onChange(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onChange, maxSize, isImage, allowedTypes],
  );

  const handleRemove = useCallback(() => {
    onChange(null);
  }, [onChange]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (!file) return;

      if (file.size > maxSize) {
        toast.error(`File must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`);
        return;
      }

      if (isImage && !file.type.startsWith("image/")) {
        toast.error("Please select an image file");
        return;
      }

      onChange(file);
    },
    [disabled, maxSize, isImage, onChange],
  );

  // Image variant with preview
  if (isImage) {
    return (
      <div className="space-y-1.5">
        <div
          className={cn(
            "group relative flex items-center justify-center overflow-hidden rounded-lg border-2 border-dashed transition-colors",
            hasFile ? "border-transparent" : "border-muted-foreground/25 hover:border-primary/50",
            "aspect-[16/9] w-full max-w-sm",
            disabled && "pointer-events-none opacity-50",
          )}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {displayUrl ? (
            <>
              <img
                src={displayUrl}
                alt="Uploaded"
                className="h-full w-full object-cover"
              />
              {!disabled && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => inputRef.current?.click()}
                  >
                    Change
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={handleRemove}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
              className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-muted-foreground transition-colors hover:text-foreground"
            >
              <ImagePlus className="h-8 w-8" />
              <span className="text-sm font-medium">
                Click or drag to upload image
              </span>
              <span className="text-xs opacity-60">
                JPEG, PNG, GIF or WebP &middot; Max {Math.round(maxSize / 1024 / 1024)} MB
              </span>
            </button>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={acceptTypes}
          onChange={handleFileSelect}
          disabled={disabled}
          className="hidden"
          aria-label="Upload image"
        />
      </div>
    );
  }

  // File variant with file info
  return (
    <div className="space-y-1.5">
      <div
        className={cn(
          "group relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors",
          hasFile ? "border-primary/30 bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
          disabled && "pointer-events-none opacity-50",
        )}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {hasFile ? (
          <div className="flex w-full items-center gap-3">
            <FileIcon className="h-8 w-8 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{fileName}</p>
              {value instanceof File && (
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(value.size)}
                </p>
              )}
            </div>
            {!disabled && (
              <div className="flex gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => inputRef.current?.click()}
                >
                  Change
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemove}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="flex flex-col items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
          >
            <FileUp className="h-8 w-8" />
            <span className="text-sm font-medium">
              Click or drag to upload file
            </span>
            <span className="text-xs opacity-60">
              Max {Math.round(maxSize / 1024 / 1024)} MB
            </span>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={acceptTypes}
        onChange={handleFileSelect}
        disabled={disabled}
        className="hidden"
        aria-label="Upload file"
      />
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
