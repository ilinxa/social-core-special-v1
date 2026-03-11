"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import {
  RESPONSE_STATUS_CONFIG,
  RESPONSE_STATUS_TABS,
} from "@/features/forms/constants/form-statuses";
import {
  useTemplateList,
  useTemplateDetail,
  useResponseList,
} from "@/features/forms/hooks/use-form-queries";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AccountType } from "@/types/rbac";
import type { FormResponseListParams, ResponseStatus, FormField } from "@/types/forms";

type ResponsesPageProps = {
  accountType: AccountType;
  accountId: string;
  slug: string;
  basePath: string;
};

const PAGE_SIZE = 25;

export function ResponsesPage({
  accountType,
  accountId,
  slug,
  basePath,
}: ResponsesPageProps) {
  const router = useRouter();
  const [selectedFormId, setSelectedFormId] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  const { data: templates } = useTemplateList(accountType, accountId, {
    status: "active",
    page_size: 100,
  });

  const params: FormResponseListParams = { page, page_size: PAGE_SIZE };
  if (statusFilter !== "all") params.status = statusFilter as ResponseStatus;

  const { data: responses, isLoading: responsesLoading } = useResponseList(
    selectedFormId,
    params,
  );

  const { data: template, isLoading: templateLoading } = useTemplateDetail(
    selectedFormId,
  );

  const visibleFields = useMemo(() => {
    if (!template?.fields) return [];
    return [...template.fields]
      .filter((f) => !f.is_hidden)
      .sort((a, b) => a.order - b.order);
  }, [template?.fields]);

  const isLoading = responsesLoading || templateLoading;
  const totalPages = responses ? Math.ceil(responses.count / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => router.push(basePath)}>
          &larr; Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Form Responses</h1>
      </div>

      {/* Form selector */}
      <div className="max-w-sm space-y-1.5">
        <Label>Select Form</Label>
        <Select
          value={selectedFormId}
          onValueChange={(v) => {
            setSelectedFormId(v);
            setPage(1);
            setStatusFilter("all");
          }}
        >
          <SelectTrigger>
            <SelectValue placeholder="Choose a form..." />
          </SelectTrigger>
          <SelectContent>
            {templates?.results.map((tpl) => (
              <SelectItem key={tpl.id} value={tpl.id}>
                {tpl.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedFormId ? (
        <div className="space-y-4">
          {/* Status tabs */}
          <div className="flex gap-2">
            {RESPONSE_STATUS_TABS.map((tab) => (
              <Button
                key={tab.value}
                variant={statusFilter === tab.value ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setStatusFilter(tab.value);
                  setPage(1);
                }}
              >
                {tab.label}
              </Button>
            ))}
          </div>

          {/* Data table */}
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }, (_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !responses?.results.length ? (
            <p className="py-8 text-center text-muted-foreground">
              No responses found.
            </p>
          ) : (
            <ResponseDataTable
              responses={responses.results}
              fields={visibleFields}
              onRowClick={(id) => router.push(`${basePath}/responses/${id}`)}
              startRow={(page - 1) * PAGE_SIZE + 1}
            />
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
                {responses && (
                  <> ({responses.count} total)</>
                )}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      ) : (
        <p className="py-8 text-center text-muted-foreground">
          Select a form to view its responses.
        </p>
      )}
    </div>
  );
}

// =============================================================================
// DATA TABLE
// =============================================================================

import type { FormResponseList } from "@/types/forms";

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "\u2014";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ResponseDataTable({
  responses,
  fields,
  onRowClick,
  startRow,
}: {
  responses: FormResponseList[];
  fields: FormField[];
  onRowClick: (id: string) => void;
  startRow: number;
}) {
  return (
    <div className="rounded-lg border overflow-auto max-h-[70vh]">
      <table className="w-max min-w-full text-sm border-collapse">
        <thead className="sticky top-0 z-20 bg-muted">
          <tr>
            {/* Fixed info columns */}
            <th className="sticky left-0 z-30 bg-muted px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap border-r">
              #
            </th>
            <th className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap">
              Display Name
            </th>
            <th className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap">
              Username
            </th>
            <th className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap">
              Email
            </th>
            <th className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap">
              Submitted
            </th>
            <th className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap border-r">
              Status
            </th>
            {/* Dynamic form field columns */}
            {fields.map((field) => (
              <th
                key={field.id}
                className="px-3 py-3 text-left font-medium text-muted-foreground whitespace-nowrap"
              >
                {field.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {responses.map((resp, idx) => (
            <tr
              key={resp.id}
              className="border-t cursor-pointer transition-colors hover:bg-muted/50"
              onClick={() => onRowClick(resp.id)}
            >
              {/* Row number - sticky */}
              <td className="sticky left-0 z-10 bg-background px-3 py-3 text-muted-foreground tabular-nums border-r">
                {startRow + idx}
              </td>
              {/* User info */}
              <td className="px-3 py-3 whitespace-nowrap font-medium">
                {resp.submitter_display_name}
              </td>
              <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                {resp.submitter_username}
              </td>
              <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                {resp.submitter_email}
              </td>
              <td className="px-3 py-3 whitespace-nowrap text-muted-foreground">
                {resp.submitted_at
                  ? new Date(resp.submitted_at).toLocaleString()
                  : "\u2014"}
              </td>
              <td className="px-3 py-3 whitespace-nowrap border-r">
                <StatusBadge
                  status={resp.status}
                  statusMap={RESPONSE_STATUS_CONFIG}
                />
              </td>
              {/* Form field values */}
              {fields.map((field) => (
                <td
                  key={field.id}
                  className="px-3 py-3 whitespace-nowrap max-w-75 truncate"
                  title={formatCellValue(resp.data[field.field_key])}
                >
                  {formatCellValue(resp.data[field.field_key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
