"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchRequiredFormApi,
  type FormTemplateForTransaction,
} from "@/features/transactions/api/transactions-api";
import { queryKeys } from "@/lib/query-keys";
import { useUpdateTransactionFormResponse } from "@/features/transactions/hooks/use-transaction-mutations";
import type { TransactionFormResponse } from "@/types/transactions";

interface ResubmitFormPanelProps {
  transactionId: string;
  formResponse: TransactionFormResponse;
  infoRequestedMessage: string | null;
  infoRequestedFields: string[] | null;
  onResubmit: () => void;
  isResubmitting?: boolean;
}

export function ResubmitFormPanel({
  transactionId,
  formResponse,
  infoRequestedMessage,
  infoRequestedFields,
  onResubmit,
  isResubmitting = false,
}: ResubmitFormPanelProps) {
  const { data: formData, isLoading: templateLoading } = useQuery({
    queryKey: queryKeys.transactions.requiredForm(transactionId),
    queryFn: () => fetchRequiredFormApi(transactionId),
    enabled: !!transactionId,
  });

  const updateFormResponse = useUpdateTransactionFormResponse(transactionId);

  // Initialize form data from existing response
  const [formValues, setFormValues] = useState<Record<string, unknown>>(
    () => ({ ...formResponse.data }),
  );
  const [saved, setSaved] = useState(false);

  const fields = useMemo(() => {
    const raw = formData?.form_template?.fields ?? [];
    return [...raw]
      .filter((f) => !f.is_hidden)
      .sort((a, b) => a.order - b.order);
  }, [formData?.form_template?.fields]);

  const requestedFieldSet = useMemo(
    () => new Set(infoRequestedFields ?? []),
    [infoRequestedFields],
  );

  function updateField(key: string, value: unknown) {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSaveAndResubmit() {
    try {
      // Step 1: Update form response data
      await updateFormResponse.mutateAsync({ data: formValues });
      setSaved(true);

      // Step 2: Resubmit the transaction
      onResubmit();
    } catch {
      toast.error("Failed to update form response");
    }
  }

  const isLoading = templateLoading || updateFormResponse.isPending || isResubmitting;

  if (templateLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Update Your Response</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-48 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-amber-200 dark:border-amber-800">
      <CardHeader>
        <CardTitle className="text-base">Update Your Response</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Reviewer message */}
        {infoRequestedMessage && (
          <div className="rounded-md bg-amber-50 p-3 text-sm dark:bg-amber-950/30">
            <p className="font-medium text-amber-800 dark:text-amber-200 mb-1">
              Changes requested:
            </p>
            <p className="text-amber-700 dark:text-amber-300">
              {infoRequestedMessage}
            </p>
          </div>
        )}

        {/* Editable form fields */}
        <div className="space-y-4">
          {fields.map((field) => {
            const isRequested = requestedFieldSet.has(field.field_key);
            return (
              <div
                key={field.id}
                className={
                  isRequested
                    ? "rounded-md border border-amber-300 p-3 dark:border-amber-700"
                    : ""
                }
              >
                {isRequested && (
                  <Badge
                    variant="outline"
                    className="mb-2 text-xs border-amber-400 text-amber-700"
                  >
                    Update requested
                  </Badge>
                )}
                <FormFieldEditor
                  field={field}
                  value={formValues[field.field_key]}
                  onChange={(val) => updateField(field.field_key, val)}
                  disabled={isLoading}
                />
              </div>
            );
          })}
        </div>

        {/* Save & Resubmit button */}
        <div className="flex justify-end pt-2 border-t">
          <Button
            onClick={handleSaveAndResubmit}
            disabled={isLoading}
          >
            {updateFormResponse.isPending
              ? "Saving..."
              : isResubmitting
                ? "Resubmitting..."
                : "Save & Resubmit"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// FIELD EDITOR (reuses pattern from AcceptWithFormDialog)
// =============================================================================

type FieldData = FormTemplateForTransaction["fields"][number];

function FormFieldEditor({
  field,
  value,
  onChange,
  disabled,
}: {
  field: FieldData;
  value: unknown;
  onChange: (val: unknown) => void;
  disabled?: boolean;
}) {
  const id = `resubmit-${field.field_key}`;

  switch (field.field_type) {
    case "textarea":
      return (
        <div className="space-y-1.5">
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
          <Textarea
            id={id}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );

    case "boolean":
    case "checkbox":
      return (
        <div className="flex items-center gap-2">
          <Checkbox
            id={id}
            checked={(value as boolean) ?? false}
            onCheckedChange={(checked) => onChange(checked === true)}
            disabled={disabled}
          />
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
        </div>
      );

    case "select":
      return (
        <div className="space-y-1.5">
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
          <select
            id={id}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          >
            <option value="">{field.placeholder || "Select..."}</option>
            {(field.options as Array<{ value: string; label: string }>).map(
              (opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ),
            )}
          </select>
        </div>
      );

    case "integer":
    case "decimal":
    case "currency":
    case "rating":
      return (
        <div className="space-y-1.5">
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
          <Input
            id={id}
            type="number"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );

    case "date":
      return (
        <div className="space-y-1.5">
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
          <Input
            id={id}
            type="date"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        </div>
      );

    default:
      return (
        <div className="space-y-1.5">
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
          {field.description && (
            <p className="text-xs text-muted-foreground">{field.description}</p>
          )}
          <Input
            id={id}
            type={
              field.field_type === "email"
                ? "email"
                : field.field_type === "url"
                  ? "url"
                  : field.field_type === "phone"
                    ? "tel"
                    : "text"
            }
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );
  }
}
