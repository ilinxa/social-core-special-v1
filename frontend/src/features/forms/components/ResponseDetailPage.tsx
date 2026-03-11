"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { RESPONSE_STATUS_CONFIG } from "@/features/forms/constants/form-statuses";
import {
  useResponseDetail,
  useTemplateDetail,
} from "@/features/forms/hooks/use-form-queries";
import {
  useProcessResponse,
  useVoidResponse,
} from "@/features/forms/hooks/use-form-mutations";
import type { FormField } from "@/types/forms";

type ResponseDetailPageProps = {
  responseId: string;
  basePath: string;
};

export function ResponseDetailPage({
  responseId,
  basePath,
}: ResponseDetailPageProps) {
  const router = useRouter();
  const { data: response, isLoading: responseLoading } =
    useResponseDetail(responseId);
  const { data: template, isLoading: templateLoading } = useTemplateDetail(
    response?.form_template ?? "",
  );

  const processResponse = useProcessResponse(response?.form_template ?? "");
  const voidResponse = useVoidResponse(response?.form_template ?? "");

  const isLoading = responseLoading || templateLoading;

  const sortedFields = useMemo(() => {
    const fields = template?.fields ?? [];
    return [...fields]
      .filter((f) => !f.is_hidden)
      .sort((a, b) => a.order - b.order);
  }, [template?.fields]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!response) {
    return <p className="text-muted-foreground">Response not found.</p>;
  }

  const isSubmitted = response.status === "submitted";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`${basePath}/responses`)}
        >
          &larr; Back
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {response.form_name}
            </h1>
            <StatusBadge
              status={response.status}
              statusMap={RESPONSE_STATUS_CONFIG}
            />
            <span className="text-sm text-muted-foreground">
              v{response.form_version}
            </span>
          </div>
        </div>
      </div>

      {/* Submitter info + Processing */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border p-4 text-sm space-y-2">
          <h3 className="font-medium mb-2">Submitter</h3>
          <InfoRow label="Name" value={response.submitter_display_name} />
          <InfoRow label="Username" value={response.submitter_username} />
          <InfoRow label="Email" value={response.submitter_email} />
          <InfoRow
            label="Submitted at"
            value={
              response.submitted_at
                ? new Date(response.submitted_at).toLocaleString()
                : "Not submitted"
            }
          />
        </div>

        <div className="rounded-lg border p-4 text-sm space-y-2">
          <h3 className="font-medium mb-2">Processing</h3>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Status</span>
            <StatusBadge
              status={response.status}
              statusMap={RESPONSE_STATUS_CONFIG}
            />
          </div>
          {response.processed_at && (
            <InfoRow
              label="Processed at"
              value={new Date(response.processed_at).toLocaleString()}
            />
          )}
          {response.processor_email && (
            <InfoRow label="Processed by" value={response.processor_email} />
          )}
          {response.processor_notes && (
            <InfoRow label="Notes" value={response.processor_notes} />
          )}

          {/* Actions */}
          {isSubmitted && (
            <div className="flex gap-2 pt-2 border-t mt-2">
              <Button
                size="sm"
                onClick={() =>
                  processResponse.mutate(
                    { responseId, data: { notes: "" } },
                    {
                      onSuccess: () =>
                        toast.success("Response marked as processed"),
                      onError: () =>
                        toast.error("Failed to process response"),
                    },
                  )
                }
                disabled={processResponse.isPending}
              >
                Mark as Processed
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() =>
                  voidResponse.mutate(
                    { responseId, data: { reason: "" } },
                    {
                      onSuccess: () => toast.success("Response voided"),
                      onError: () => toast.error("Failed to void response"),
                    },
                  )
                }
                disabled={voidResponse.isPending}
              >
                Void
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Response data table */}
      <div>
        <h3 className="font-medium mb-3">Response Data</h3>
        <ResponseDataTable fields={sortedFields} data={response.data} />
      </div>
    </div>
  );
}

// =============================================================================
// HELPERS
// =============================================================================

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "\u2014";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ResponseDataTable({
  fields,
  data,
}: {
  fields: FormField[];
  data: Record<string, unknown>;
}) {
  if (fields.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        No fields to display.
      </p>
    );
  }

  return (
    <div className="rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium text-muted-foreground w-1/3">
              Field
            </th>
            <th className="px-4 py-3 text-left font-medium text-muted-foreground">
              Value
            </th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field, idx) => (
            <tr
              key={field.id}
              className={idx < fields.length - 1 ? "border-b" : ""}
            >
              <td className="px-4 py-3 font-medium text-muted-foreground">
                {field.label}
              </td>
              <td className="px-4 py-3">{formatValue(data[field.field_key])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
