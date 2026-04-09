/**
 * Media Picker Dialog
 * ====================
 * Dialog for selecting a media file from the CMS media library.
 * Used by CmsFieldRenderer for "media" field type.
 */

"use client";

import { useState } from "react";
import { Check, FileImage } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useMediaFiles } from "@/features/cms/hooks/use-cms-queries";
import type { CmsApiContext, CmsMediaFile } from "@/features/cms/types";

type MediaPickerDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: CmsApiContext;
  onSelect: (mediaId: string, filename: string) => void;
};

export function MediaPickerDialog({
  open,
  onOpenChange,
  context,
  onSelect,
}: MediaPickerDialogProps) {
  const { data, isLoading } = useMediaFiles(context);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState("");

  function handleConfirm() {
    if (selectedId) {
      onSelect(selectedId, selectedName);
      onOpenChange(false);
      setSelectedId(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Select Media</DialogTitle>
        </DialogHeader>

        <div className="max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="grid grid-cols-4 gap-2">
              {Array.from({ length: 8 }, (_, i) => (
                <Skeleton key={i} className="aspect-square rounded" />
              ))}
            </div>
          ) : !data?.results.length ? (
            <div className="flex flex-col items-center justify-center gap-2 py-12">
              <FileImage className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No media files. Upload some first.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-2">
              {data.results.map((file: CmsMediaFile) => (
                <button
                  key={file.id}
                  type="button"
                  className={cn(
                    "relative flex aspect-square flex-col items-center justify-center gap-1 rounded border p-2 text-center transition-colors",
                    selectedId === file.id
                      ? "border-primary bg-primary/10"
                      : "hover:bg-muted/50",
                  )}
                  onClick={() => {
                    setSelectedId(file.id);
                    setSelectedName(file.original_filename);
                  }}
                >
                  <FileImage className="h-6 w-6 text-muted-foreground" />
                  <p className="max-w-full truncate text-xs">
                    {file.original_filename}
                  </p>
                  {selectedId === file.id && (
                    <div className="absolute right-1 top-1">
                      <Check className="h-4 w-4 text-primary" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedId}>
            Select
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
