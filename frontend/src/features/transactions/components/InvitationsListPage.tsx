"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Can } from "@/components/common/Can";
import { useHasPermission } from "@/hooks/use-has-permission";
import { TransactionList } from "./TransactionList";
import { InvitationCreateDialog } from "./InvitationCreateDialog";
import { useTransactionList } from "@/features/transactions/hooks/use-transaction-queries";
import { useCancelTransaction } from "@/features/transactions/hooks/use-transaction-mutations";
import type { TransactionListParams } from "@/types/transactions";
import type { AccountType } from "@/types/rbac";

interface InvitationsListPageProps {
  accountType: AccountType;
  accountId: string;
  slug: string;
  actorRoleLevel: number;
  maxMembers?: number;
  basePath: string;
}

export function InvitationsListPage({
  accountType,
  accountId,
  slug,
  actorRoleLevel,
  maxMembers = 0,
  basePath,
}: InvitationsListPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [createOpen, setCreateOpen] = useState(false);
  // Only user-mutable filters in state; context params derived from props
  // so they always reflect the latest accountId (avoids stale useState).
  const [filters, setFilters] = useState<Partial<TransactionListParams>>({});

  const params = useMemo<TransactionListParams>(
    () => ({
      mode: "invitation",
      context_type: accountType,
      context_id: accountId,
      ...filters,
    }),
    [accountType, accountId, filters],
  );

  const { data, isLoading, refetch } = useTransactionList(
    accountId ? params : undefined,
  );
  const cancelTransaction = useCancelTransaction();
  const canInvite = useHasPermission("can_invite_member", accountType, accountId);

  function handleCancel(transactionId: string) {
    cancelTransaction.mutate(
      { transactionId },
      { onSuccess: () => refetch() },
    );
  }

  // Open dialog when ?create=true is in URL
  useEffect(() => {
    if (searchParams.get("create") === "true") {
      setCreateOpen(true);
    }
  }, [searchParams]);

  function handleCreateOpenChange(open: boolean) {
    setCreateOpen(open);
    // Refetch list when dialog closes (invitation may have been created)
    if (!open) {
      refetch();
    }
    // Remove ?create=true from URL when closing
    if (!open && searchParams.get("create") === "true") {
      router.replace(`${basePath}/invitations`);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Invitations</h1>
      <TransactionList
        data={data}
        params={params}
        onParamsChange={(p) => setFilters({ status: p.status, page: p.page })}
        onTransactionClick={(id) => router.push(`${basePath}/invitations/${id}`)}
        onCancelTransaction={handleCancel}
        isCancelling={cancelTransaction.isPending}
        isLoading={isLoading}
        title="Sent Invitations"
        headerAction={
          <Can allowed={canInvite}>
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              New Invitation
            </Button>
          </Can>
        }
      />

      <InvitationCreateDialog
        open={createOpen}
        onOpenChange={handleCreateOpenChange}
        accountType={accountType}
        accountId={accountId}
        slug={slug}
        actorRoleLevel={actorRoleLevel}
        maxMembers={maxMembers}
      />
    </div>
  );
}
