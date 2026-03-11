"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { FormTemplateForTransaction } from "@/features/transactions/api/transactions-api";
import {
  TransactionFormFieldInput,
  uploadFilesInFormData,
} from "@/features/transactions/components/TransactionFormFields";

interface RequestWithFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  formTemplateName: string;
  formTemplate: FormTemplateForTransaction | null;
  isLoadingTemplate?: boolean;
  onSubmit: (formData: Record<string, unknown>) => void;
  isSubmitting?: boolean;
  error?: string | null;
}

export function RequestWithFormDialog({
  open,
  onOpenChange,
  formTemplateName,
  formTemplate,
  isLoadingTemplate,
  onSubmit,
  isSubmitting,
  error,
}: RequestWithFormDialogProps) {
  const fields = formTemplate?.fields ?? [];
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  function updateField(key: string, value: unknown) {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    setUploadError(null);
    setUploading(true);
    try {
      const uploaded = await uploadFilesInFormData(formData);
      onSubmit(uploaded);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Failed to upload file",
      );
    } finally {
      setUploading(false);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setFormData({});
      setUploadError(null);
    }
    onOpenChange(nextOpen);
  }

  const isLoading = isLoadingTemplate || isSubmitting || uploading;
  const displayError = uploadError || error;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Complete Form to Request</DialogTitle>
          <DialogDescription>
            This organization requires you to fill out the form
            &quot;{formTemplateName}&quot; before submitting your membership
            request.
          </DialogDescription>
        </DialogHeader>

        {isLoadingTemplate ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {fields
              .filter((f) => !f.is_hidden)
              .sort((a, b) => a.order - b.order)
              .map((field) => (
                <TransactionFormFieldInput
                  key={field.id}
                  field={field}
                  value={formData[field.field_key]}
                  onChange={(val) => updateField(field.field_key, val)}
                  disabled={isLoading}
                />
              ))}

            {fields.filter((f) => !f.is_hidden).length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No fields to fill out.
              </p>
            )}
          </div>
        )}

        {displayError && (
          <p className="text-sm text-destructive">{displayError}</p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || isLoadingTemplate}
          >
            {uploading
              ? "Uploading..."
              : isSubmitting
                ? "Submitting..."
                : "Submit & Request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
