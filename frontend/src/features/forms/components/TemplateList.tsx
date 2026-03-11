"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { FORM_STATUS_CONFIG } from "@/features/forms/constants/form-statuses";
import type { PaginatedResponse } from "@/types";
import type { FormTemplateList, FormStatus } from "@/types/forms";

type TemplateListProps = {
  data?: PaginatedResponse<FormTemplateList>;
  isLoading?: boolean;
  statusFilter?: string;
  onStatusChange?: (status: string) => void;
  onTemplateClick?: (id: string) => void;
  onCreateClick?: () => void;
  canCreate?: boolean;
  page?: number;
  onPageChange?: (page: number) => void;
};

const STATUS_TABS = ["all", "active", "draft", "archived"] as const;

export function TemplateList({
  data,
  isLoading,
  statusFilter = "all",
  onStatusChange,
  onTemplateClick,
  onCreateClick,
  canCreate,
  page = 1,
  onPageChange,
}: TemplateListProps) {
  const totalPages = data ? Math.ceil(data.count / 10) : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Form Templates</h2>
        {canCreate && (
          <Button size="sm" onClick={onCreateClick}>
            New Form
          </Button>
        )}
      </div>

      {/* Status tabs */}
      <div className="flex gap-2">
        {STATUS_TABS.map((tab) => (
          <Button
            key={tab}
            variant={statusFilter === tab ? "default" : "outline"}
            size="sm"
            onClick={() => onStatusChange?.(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Button>
        ))}
      </div>

      {/* Template list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No templates found.
        </p>
      ) : (
        <div className="space-y-2">
          {data.results.map((tpl) => (
            <button
              key={tpl.id}
              className="flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
              onClick={() => onTemplateClick?.(tpl.id)}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{tpl.name}</span>
                  {tpl.is_template_public && (
                    <Badge variant="secondary">Public</Badge>
                  )}
                </div>
                {tpl.description && (
                  <p className="text-sm text-muted-foreground line-clamp-1">
                    {tpl.description}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">
                  v{tpl.version}
                </span>
                <StatusBadge
                  status={tpl.status}
                  statusMap={FORM_STATUS_CONFIG}
                />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => onPageChange?.(page - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => onPageChange?.(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
