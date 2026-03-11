"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

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
import {
  fetchRequiredFormApi,
  submitRequiredFormApi,
} from "@/features/transactions/api/transactions-api";
import {
  TransactionFormFieldInput,
  uploadFilesInFormData,
} from "@/features/transactions/components/TransactionFormFields";

interface AcceptWithFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transactionId: string;
  formTemplateName: string;
  onAcceptWithForm: (formResponseId: string) => void;
  isAccepting?: boolean;
}

export function AcceptWithFormDialog({
  open,
  onOpenChange,
  transactionId,
  formTemplateName,
  onAcceptWithForm,
  isAccepting,
}: AcceptWithFormDialogProps) {
  const { data, isLoading: templateLoading } = useQuery({
    queryKey: ["transactions", "required-form", transactionId],
    queryFn: () => fetchRequiredFormApi(transactionId),
    enabled: open && !!transactionId,
  });

  const template = data?.form_template;
  const fields = template?.fields ?? [];
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isLoading = templateLoading || submitting || isAccepting;

  function updateField(key: string, value: unknown) {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmitAndAccept() {
    if (!template) return;
    setError(null);
    setSubmitting(true);

    try {
      // Upload any File objects first, then submit
      const uploadedData = await uploadFilesInFormData(formData);

      // Create and submit form response via transaction-scoped endpoint
      const response = await submitRequiredFormApi(transactionId, uploadedData);

      // Accept the transaction with the form response ID
      onAcceptWithForm(response.id);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to submit form";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Complete Form to Accept</DialogTitle>
          <DialogDescription>
            Please fill out the required form &quot;{formTemplateName}&quot;
            before accepting this transaction.
          </DialogDescription>
        </DialogHeader>

        {templateLoading ? (
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

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmitAndAccept}
            disabled={isLoading || templateLoading}
          >
            {submitting
              ? "Submitting..."
              : isAccepting
                ? "Accepting..."
                : "Submit & Accept"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
