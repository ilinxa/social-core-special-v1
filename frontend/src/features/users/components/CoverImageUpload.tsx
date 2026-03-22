"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ImagePlus, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  useUploadCoverImage,
  useDeleteCoverImage,
} from "@/features/users/hooks/use-user-mutations";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

interface CoverImageUploadProps {
  coverImageUrl: string | null;
  hasCoverImage: boolean;
}

export function CoverImageUpload({ coverImageUrl, hasCoverImage }: CoverImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const uploadCover = useUploadCoverImage();
  const deleteCover = useDeleteCoverImage();

  const isUploading = uploadCover.isPending;
  const isRemoving = deleteCover.isPending;
  const displayUrl = previewUrl ?? coverImageUrl;

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > MAX_FILE_SIZE) {
        toast.error("Image must be smaller than 5 MB");
        return;
      }

      if (!ACCEPTED_TYPES.includes(file.type)) {
        toast.error("Only JPEG, PNG, GIF, and WebP images are allowed");
        return;
      }

      const preview = URL.createObjectURL(file);
      setPreviewUrl(preview);

      try {
        await uploadCover.mutateAsync(file);
      } catch {
        setPreviewUrl(null);
        toast.error("Failed to upload cover image");
      }

      if (inputRef.current) inputRef.current.value = "";
    },
    [uploadCover],
  );

  const handleRemove = useCallback(async () => {
    try {
      await deleteCover.mutateAsync();
      setPreviewUrl(null);
    } catch {
      toast.error("Failed to remove cover image");
    }
  }, [deleteCover]);

  return (
    <div className="space-y-3">
      {/* Cover image preview / placeholder */}
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="group relative w-full cursor-pointer overflow-hidden rounded-lg border-2 border-dashed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {displayUrl ? (
          <img
            src={displayUrl}
            alt="Cover image"
            className="aspect-[3/1] w-full object-cover"
          />
        ) : (
          <div className="flex aspect-[3/1] w-full flex-col items-center justify-center gap-1.5 text-muted-foreground transition-colors group-hover:text-foreground">
            <ImagePlus className="h-8 w-8" />
            <span className="text-sm font-medium">Upload Cover Image</span>
            <span className="text-xs opacity-60">Recommended: 1500 x 500px</span>
          </div>
        )}

        {/* Hover overlay when image exists */}
        {displayUrl && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
            {isUploading ? (
              <Loader2 className="h-8 w-8 animate-spin text-white" />
            ) : (
              <span className="text-sm font-medium text-white">Change Cover Image</span>
            )}
          </div>
        )}
      </button>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          <ImagePlus className="mr-1.5 h-3.5 w-3.5" />
          {isUploading ? "Uploading..." : hasCoverImage ? "Change" : "Upload"}
        </Button>

        {hasCoverImage && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleRemove}
            disabled={isRemoving}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
            {isRemoving ? "Removing..." : "Remove"}
          </Button>
        )}

        <span className="text-muted-foreground text-xs">
          JPG, PNG, GIF or WebP. Max 5 MB.
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFileChange}
        className="hidden"
        aria-label="Upload cover image"
      />
    </div>
  );
}
