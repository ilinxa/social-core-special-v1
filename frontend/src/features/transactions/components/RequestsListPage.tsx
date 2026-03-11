"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { TransactionList } from "./TransactionList";
import { useTransactionList } from "@/features/transactions/hooks/use-transaction-queries";
import {
  useAcceptTransaction,
  useDenyTransaction,
} from "@/features/transactions/hooks/use-transaction-mutations";
import type { TransactionListParams } from "@/types/transactions";

interface RequestsListPageProps {
  accountType: string;
  accountId: string;
  basePath: string;
}

export function RequestsListPage({
  accountType,
  accountId,
  basePath,
}: RequestsListPageProps) {
  const router = useRouter();
  // Only user-mutable filters in state; context params derived from props
  // so they always reflect the latest accountId (avoids stale useState).
  const [filters, setFilters] = useState<Partial<TransactionListParams>>({});

  const params = useMemo<TransactionListParams>(
    () => ({
      mode: "request",
      context_type: accountType,
      context_id: accountId,
      ...filters,
    }),
    [accountType, accountId, filters],
  );

  const { data, isLoading, refetch } = useTransactionList(
    accountId ? params : undefined,
  );
  const accept = useAcceptTransaction();
  const deny = useDenyTransaction();

  const isActioning = accept.isPending || deny.isPending;

  function handleAccept(transactionId: string) {
    accept.mutate(
      { transactionId },
      {
        onSuccess: () => {
          toast.success("Request accepted");
          refetch();
        },
        onError: () => toast.error("Failed to accept request"),
      },
    );
  }

  function handleDeny(transactionId: string, reason?: string) {
    deny.mutate(
      {
        transactionId,
        data: reason ? { reason } : undefined,
      },
      {
        onSuccess: () => {
          toast.success("Request denied");
          refetch();
        },
        onError: () => toast.error("Failed to deny request"),
      },
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Requests</h1>
      <TransactionList
        data={data}
        params={params}
        onParamsChange={(p) => setFilters({ status: p.status, page: p.page })}
        onTransactionClick={(id) => router.push(`${basePath}/requests/${id}`)}
        onAcceptTransaction={handleAccept}
        onDenyTransaction={handleDeny}
        isActioning={isActioning}
        isLoading={isLoading}
        title="Incoming Requests"
      />
    </div>
  );
}
