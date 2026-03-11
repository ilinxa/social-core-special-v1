"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ImagePlus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

interface ImageUploadProps {
  currentUrl: string | null;
  value: File | null;
  onChange: (file: File | null) => void;
  label: string;
  aspectHint?: string;
  shape?: "square" | "wide";
  maxSize?: number;
  disabled?: boolean;
}

export function ImageUpload({
  currentUrl,
  value,
  onChange,
  label,
  aspectHint,
  shape = "square",
  maxSize = MAX_FILE_SIZE,
  disabled,
}: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Create/cleanup object URL for selected file
  useEffect(() => {
    if (!value) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(value);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  const displayUrl = previewUrl ?? currentUrl;
  const hasImage = !!displayUrl;

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > maxSize) {
        toast.error(`Image must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`);
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      if (!ACCEPTED_TYPES.includes(file.type)) {
        toast.error("Only JPEG, PNG, GIF, and WebP images are allowed");
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      onChange(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onChange, maxSize],
  );

  const handleRemove = useCallback(() => {
    onChange(null);
  }, [onChange]);

  return (
    <div className="space-y-2">
      <Label>{label}</Label>

      <div
        className={cn(
          "group relative overflow-hidden rounded-lg border-2 border-dashed",
          hasImage ? "border-transparent" : "border-muted-foreground/25",
          shape === "square" ? "aspect-square w-32" : "aspect-[16/9] w-full max-w-md",
          disabled && "opacity-50",
        )}
      >
        {hasImage ? (
          <img
            src={displayUrl!}
            alt={label}
            className="h-full w-full object-cover"
          />
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <ImagePlus className="h-6 w-6" />
            <span className="text-xs font-medium">Upload {label}</span>
            {aspectHint && <span className="text-xs opacity-60">{aspectHint}</span>}
          </button>
        )}

        {/* Hover overlay when image exists */}
        {hasImage && !disabled && (
          <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
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
      </div>

      <p className="text-muted-foreground text-xs">
        JPG, PNG, GIF or WebP. Max {Math.round(maxSize / 1024 / 1024)} MB.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFileChange}
        disabled={disabled}
        className="hidden"
        aria-label={`Upload ${label}`}
      />
    </div>
  );
}
