"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { RESPONSE_STATUS_CONFIG } from "@/features/forms/constants/form-statuses";
import type { PaginatedResponse } from "@/types";
import type { FormResponseList, ResponseStatus } from "@/types/forms";

type ResponseListProps = {
  data?: PaginatedResponse<FormResponseList>;
  isLoading?: boolean;
  statusFilter?: string;
  onStatusChange?: (status: string) => void;
  onResponseClick?: (id: string) => void;
  page?: number;
  onPageChange?: (page: number) => void;
};

const STATUS_TABS = ["all", "submitted", "draft", "processed", "void"] as const;

export function ResponseList({
  data,
  isLoading,
  statusFilter = "all",
  onStatusChange,
  onResponseClick,
  page = 1,
  onPageChange,
}: ResponseListProps) {
  const totalPages = data ? Math.ceil(data.count / 10) : 0;

  return (
    <div className="space-y-4">
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

      {/* Response list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No responses found.
        </p>
      ) : (
        <div className="space-y-2">
          {data.results.map((resp) => (
            <button
              key={resp.id}
              className="flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
              onClick={() => onResponseClick?.(resp.id)}
            >
              <div className="space-y-1">
                <span className="font-medium">{resp.form_name}</span>
                <p className="text-sm text-muted-foreground">
                  {resp.submitter_email} &middot; v{resp.form_version}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {resp.submitted_at && (
                  <span className="text-sm text-muted-foreground">
                    {new Date(resp.submitted_at).toLocaleDateString()}
                  </span>
                )}
                <StatusBadge
                  status={resp.status}
                  statusMap={RESPONSE_STATUS_CONFIG}
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
