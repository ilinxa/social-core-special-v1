"use client";

import { useState } from "react";
import { ArrowRightLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useGovernanceTransactions } from "@/features/governance/hooks/use-governance-queries";
import type { TransactionListItem } from "@/types/transactions";

const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "denied", label: "Denied" },
  { value: "cancelled", label: "Cancelled" },
  { value: "expired", label: "Expired" },
];

const MODE_OPTIONS = [
  { value: "all", label: "All Modes" },
  { value: "invitation", label: "Invitation" },
  { value: "request", label: "Request" },
];

const CONTEXT_TYPE_OPTIONS = [
  { value: "all", label: "All Contexts" },
  { value: "business", label: "Business" },
  { value: "platform", label: "Platform" },
];

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "pending":
      return "outline";
    case "accepted":
      return "default";
    case "denied":
      return "destructive";
    case "cancelled":
    case "expired":
      return "secondary";
    default:
      return "secondary";
  }
}

export function GovernanceTransactionsPage() {
  const [status, setStatus] = useState("all");
  const [mode, setMode] = useState("all");
  const [contextType, setContextType] = useState("all");
  const [page, setPage] = useState(1);

  const params: Record<string, unknown> = { page, page_size: 20 };
  if (status !== "all") params.status = status;
  if (mode !== "all") params.mode = mode;
  if (contextType !== "all") params.context_type = contextType;

  const { data, isLoading } = useGovernanceTransactions(params);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">
        Transaction Overview
      </h1>

      {/* Filter bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={mode}
          onValueChange={(v) => {
            setMode(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Mode" />
          </SelectTrigger>
          <SelectContent>
            {MODE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={contextType}
          onValueChange={(v) => {
            setContextType(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Context" />
          </SelectTrigger>
          <SelectContent>
            {CONTEXT_TYPE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="text-muted-foreground py-12 text-center">
          No transactions found.
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} {data.count === 1 ? "transaction" : "transactions"}
          </p>
          <div className="space-y-2">
            {data.results.map((txn) => (
              <TransactionCard key={txn.id} transaction={txn} />
            ))}
          </div>

          {(data.previous || data.next) && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!data.previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-muted-foreground text-sm">Page {page}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function TransactionCard({
  transaction,
}: {
  transaction: TransactionListItem;
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border p-4">
      <div className="bg-muted flex h-9 w-9 items-center justify-center rounded-lg">
        <ArrowRightLeft className="text-muted-foreground h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{transaction.transaction_type}</p>
          <Badge variant={statusBadgeVariant(transaction.status)}>
            {transaction.status}
          </Badge>
          <Badge variant="outline">{transaction.mode}</Badge>
        </div>
        <p className="text-muted-foreground text-sm">
          {transaction.initiator_name || "Unknown"} &rarr;{" "}
          {transaction.target_name || "Unknown"} &middot;{" "}
          {transaction.context_type}
        </p>
      </div>
      <div className="text-muted-foreground hidden text-sm sm:block">
        {new Date(transaction.created_at).toLocaleDateString()}
      </div>
    </div>
  );
}
