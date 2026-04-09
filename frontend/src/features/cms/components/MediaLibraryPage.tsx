/**
 * Media Library Page
 * ===================
 * Grid/list view of media files with upload, detail panel, and delete.
 * Shared between platform and business contexts.
 */

"use client";

import { useCallback, useRef, useState } from "react";
import {
  FileImage,
  Grid,
  List,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropZone } from "@/features/cms/components/DropZone";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Can } from "@/components/common/Can";
import { QuotaBar } from "@/components/common/QuotaBar";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { ApiError } from "@/lib/api-client";
import {
  ALLOWED_MEDIA_EXTENSIONS,
  DEFAULT_MAX_MEDIA_FILE_SIZE_MB,
} from "@/features/cms/constants/cms-constants";
import { useMediaFiles } from "@/features/cms/hooks/use-cms-queries";
import {
  useDeleteMediaFile,
  useUploadMediaFile,
} from "@/features/cms/hooks/use-cms-mutations";
import type {
  CmsApiContext,
  CmsMediaFile,
  CmsPermissions,
} from "@/features/cms/types";

type MediaLibraryPageProps = {
  context: CmsApiContext;
  permissions?: CmsPermissions | null;
  maxFiles?: number;
};

export function MediaLibraryPage({
  context,
  permissions,
  maxFiles = 0,
}: MediaLibraryPageProps) {
  const { data, isLoading } = useMediaFiles(context);
  const uploadMutation = useUploadMediaFile(context);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selectedFile, setSelectedFile] = useState<CmsMediaFile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CmsMediaFile | null>(null);

  const deleteMutation = useDeleteMediaFile(
    context,
    deleteTarget?.id ?? "",
  );

  const validateAndUpload = useCallback(
    (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
      if (!ALLOWED_MEDIA_EXTENSIONS.has(ext)) {
        toast.error(`File type .${ext} is not allowed`);
        return;
      }
      if (file.size > DEFAULT_MAX_MEDIA_FILE_SIZE_MB * 1024 * 1024) {
        toast.error(
          `File exceeds ${DEFAULT_MAX_MEDIA_FILE_SIZE_MB}MB limit`,
        );
        return;
      }
      const formData = new FormData();
      formData.append("file", file);
      uploadMutation.mutate(formData, {
        onSuccess: () => toast.success("File uploaded"),
        onError: (error) => {
          if (error instanceof ApiError && error.details?.rule) {
            toast.error(
              `Upload failed: ${String(error.details.rule).replace(/_/g, " ")}`,
            );
          } else {
            toast.error("Upload failed");
          }
        },
      });
    },
    [uploadMutation],
  );

  const handleUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      validateAndUpload(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [validateAndUpload],
  );

  const handleDrop = useCallback(
    (files: FileList) => {
      for (let i = 0; i < files.length; i++) {
        validateAndUpload(files[i]);
      }
    },
    [validateAndUpload],
  );

  function handleDelete() {
    if (!deleteTarget) return;
    deleteMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success("File deleted");
        setDeleteTarget(null);
        setSelectedFile(null);
      },
      onError: () => toast.error("Delete failed"),
    });
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <DropZone onDrop={handleDrop} disabled={uploadMutation.isPending}>
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Media Library</h1>
          <p className="text-sm text-muted-foreground">
            Upload and manage media files.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Grid view"
            onClick={() => setViewMode("grid")}
            className={viewMode === "grid" ? "bg-muted" : ""}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label="List view"
            onClick={() => setViewMode("list")}
            className={viewMode === "list" ? "bg-muted" : ""}
          >
            <List className="h-4 w-4" />
          </Button>
          <Can allowed={permissions?.can_upload_media ?? true}>
            <Button
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              <Upload className="mr-1.5 h-4 w-4" />
              {uploadMutation.isPending ? "Uploading..." : "Upload"}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleUpload}
              accept={Array.from(ALLOWED_MEDIA_EXTENSIONS)
                .map((e) => `.${e}`)
                .join(",")}
            />
          </Can>
        </div>
      </div>

      {/* Quota */}
      {maxFiles > 0 && data && (
        <QuotaBar
          current={data.results.length}
          max={maxFiles}
          label="Media files"
        />
      )}

      {/* File grid/list */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16">
          <FileImage className="h-12 w-12 text-muted-foreground" />
          <p className="text-muted-foreground">No media files yet.</p>
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {data.results.map((file: CmsMediaFile) => (
            <button
              key={file.id}
              type="button"
              className="group relative aspect-square overflow-hidden rounded-lg border transition-colors hover:border-primary"
              onClick={() => setSelectedFile(file)}
            >
              {file.mime_type.startsWith("image/") ? (
                <div className="flex h-full items-center justify-center bg-muted p-2 text-xs text-muted-foreground">
                  {file.original_filename}
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center gap-2 bg-muted">
                  <FileImage className="h-8 w-8 text-muted-foreground" />
                  <p className="px-2 text-center text-xs text-muted-foreground truncate max-w-full">
                    {file.original_filename}
                  </p>
                </div>
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-linear-to-t from-black/60 to-transparent p-2">
                <p className="truncate text-xs text-white">
                  {formatFileSize(file.file_size)}
                </p>
              </div>
              {file.is_tombstoned && (
                <Badge
                  variant="destructive"
                  className="absolute right-1 top-1 text-xs"
                >
                  Tombstoned
                </Badge>
              )}
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {data.results.map((file: CmsMediaFile) => (
            <button
              key={file.id}
              type="button"
              className="flex w-full items-center justify-between rounded-lg border p-3 text-left transition-colors hover:bg-muted/50"
              onClick={() => setSelectedFile(file)}
            >
              <div className="flex items-center gap-3">
                <FileImage className="h-5 w-5 shrink-0 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">
                    {file.original_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {file.mime_type} &middot; {formatFileSize(file.file_size)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {file.is_tombstoned && (
                  <Badge variant="destructive" className="text-xs">
                    Tombstoned
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {file.usage_count} uses
                </Badge>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* File detail sheet */}
      <Sheet
        open={selectedFile !== null}
        onOpenChange={(v) => !v && setSelectedFile(null)}
      >
        <SheetContent>
          {selectedFile && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedFile.original_filename}</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Type
                  </p>
                  <p className="text-sm">{selectedFile.mime_type}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Size
                  </p>
                  <p className="text-sm">
                    {formatFileSize(selectedFile.file_size)}
                  </p>
                </div>
                {selectedFile.width && selectedFile.height && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-muted-foreground">
                      Dimensions
                    </p>
                    <p className="text-sm">
                      {selectedFile.width} &times; {selectedFile.height}
                    </p>
                  </div>
                )}
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Alt Text
                  </p>
                  <p className="text-sm">
                    {selectedFile.alt_text || "None"}
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Usage
                  </p>
                  <p className="text-sm">
                    Referenced by {selectedFile.usage_count} block(s)
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Uploaded
                  </p>
                  <p className="text-sm">
                    {new Date(selectedFile.created_at).toLocaleString()}
                  </p>
                </div>
                <Can allowed={permissions?.can_delete_media ?? true}>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="w-full"
                    onClick={() => setDeleteTarget(selectedFile)}
                  >
                    <Trash2 className="mr-1.5 h-4 w-4" />
                    Delete File
                  </Button>
                </Can>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete confirmation */}
      <ConfirmActionDialog
        open={deleteTarget !== null}
        onOpenChange={(v) => !v && setDeleteTarget(null)}
        title="Delete Media File"
        description={`Delete "${deleteTarget?.original_filename}"? Files with published references will be tombstoned instead of deleted.`}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
    </DropZone>
  );
}
