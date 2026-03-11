"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TransactionCard } from "./TransactionCard";
import {
  TRANSACTION_STATUS_TABS,
  TRANSACTION_CATEGORY_CONFIG,
} from "@/features/transactions/constants/transaction-statuses";
import type { PaginatedResponse } from "@/types";
import type {
  TransactionListItem,
  TransactionListParams,
  TransactionCategory,
} from "@/types/transactions";

interface TransactionListProps {
  data?: PaginatedResponse<TransactionListItem>;
  params: TransactionListParams;
  onParamsChange: (params: TransactionListParams) => void;
  onTransactionClick: (id: string) => void;
  onCancelTransaction?: (id: string) => void;
  onAcceptTransaction?: (id: string) => void;
  onDenyTransaction?: (id: string, reason?: string) => void;
  isCancelling?: boolean;
  isActioning?: boolean;
  isLoading?: boolean;
  headerAction?: React.ReactNode;
  title?: string;
}

export function TransactionList({
  data,
  params,
  onParamsChange,
  onTransactionClick,
  onCancelTransaction,
  onAcceptTransaction,
  onDenyTransaction,
  isCancelling,
  isActioning,
  isLoading,
  headerAction,
  title = "Transactions",
}: TransactionListProps) {
  const currentPage = params.page ?? 1;
  const pageSize = params.page_size ?? 20;
  const totalPages = data ? Math.ceil(data.count / pageSize) : 0;

  function handleStatusChange(status: string) {
    onParamsChange({
      ...params,
      status: status === "all" ? undefined : (status as TransactionListParams["status"]),
      page: 1,
    });
  }

  function handleCategoryChange(category: string) {
    onParamsChange({
      ...params,
      context_type: category === "all" ? undefined : category,
      page: 1,
    });
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        {headerAction}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {TRANSACTION_STATUS_TABS.map((tab) => (
          <Button
            key={tab.value}
            variant={(params.status ?? "all") === tab.value ? "default" : "outline"}
            size="sm"
            onClick={() => handleStatusChange(tab.value)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No transactions found.
        </p>
      ) : (
        <div className="space-y-2">
          {data.results.map((txn) => (
            <TransactionCard
              key={txn.id}
              transaction={txn}
              onClick={() => onTransactionClick(txn.id)}
              onCancel={onCancelTransaction}
              onAccept={onAcceptTransaction}
              onDeny={onDenyTransaction}
              isCancelling={isCancelling}
              isActioning={isActioning}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {data?.count} total
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => onParamsChange({ ...params, page: currentPage - 1 })}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => onParamsChange({ ...params, page: currentPage + 1 })}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
