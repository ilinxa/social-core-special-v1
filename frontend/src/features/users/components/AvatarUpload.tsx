"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useUploadAvatar, useDeleteAvatar } from "@/features/users/hooks/use-user-mutations";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

interface AvatarUploadProps {
  avatarUrl: string | null;
  hasAvatar: boolean;
  fallbackText: string;
}

export function AvatarUpload({ avatarUrl, hasAvatar, fallbackText }: AvatarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const uploadAvatar = useUploadAvatar();
  const deleteAvatar = useDeleteAvatar();

  const isUploading = uploadAvatar.isPending;
  const isRemoving = deleteAvatar.isPending;
  const displayUrl = previewUrl ?? avatarUrl ?? undefined;

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
        await uploadAvatar.mutateAsync(file);
      } catch {
        setPreviewUrl(null);
        toast.error("Failed to upload avatar");
      }

      if (inputRef.current) inputRef.current.value = "";
    },
    [uploadAvatar],
  );

  const handleRemove = useCallback(async () => {
    try {
      await deleteAvatar.mutateAsync();
      setPreviewUrl(null);
    } catch {
      toast.error("Failed to remove avatar");
    }
  }, [deleteAvatar]);

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
      {/* Avatar with hover overlay */}
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="group relative cursor-pointer rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
      >
        <Avatar className="size-24">
          <AvatarImage src={displayUrl} alt="Profile avatar" />
          <AvatarFallback className="bg-muted text-2xl font-semibold">
            {fallbackText}
          </AvatarFallback>
        </Avatar>

        {/* Hover overlay */}
        <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          {isUploading ? (
            <Loader2 className="h-6 w-6 animate-spin text-white" />
          ) : (
            <Camera className="h-6 w-6 text-white" />
          )}
        </div>
      </button>

      {/* Actions */}
      <div className="flex flex-col items-center gap-1.5 sm:items-start sm:pt-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          <Camera className="mr-1.5 h-3.5 w-3.5" />
          {isUploading ? "Uploading..." : "Change Photo"}
        </Button>

        {hasAvatar && (
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

        <p className="text-muted-foreground mt-1 text-xs">
          JPG, PNG, GIF or WebP. Max 5 MB.
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFileChange}
        className="hidden"
        aria-label="Upload avatar"
      />
    </div>
  );
}
