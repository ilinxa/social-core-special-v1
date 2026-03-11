"use client";

import { useState } from "react";

import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TRANSACTION_STATUS_CONFIG,
  TRANSACTION_CATEGORY_CONFIG,
} from "@/features/transactions/constants/transaction-statuses";
import type { TransactionListItem } from "@/types/transactions";

interface TransactionCardProps {
  transaction: TransactionListItem;
  onClick?: () => void;
  onCancel?: (id: string) => void;
  onAccept?: (id: string) => void;
  onDeny?: (id: string, reason?: string) => void;
  isCancelling?: boolean;
  isActioning?: boolean;
}

export function TransactionCard({
  transaction,
  onClick,
  onCancel,
  onAccept,
  onDeny,
  isCancelling,
  isActioning,
}: TransactionCardProps) {
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);
  const [confirmDenyOpen, setConfirmDenyOpen] = useState(false);
  const categoryConfig = TRANSACTION_CATEGORY_CONFIG[transaction.category];
  const isPending = transaction.status === "pending";
  const showCancel =
    onCancel && (isPending || transaction.status === "info_requested");
  const showAcceptDeny = isPending && (onAccept || onDeny);

  return (
    <div className="flex w-full items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50">
      <button
        className="flex flex-1 items-center justify-between text-left"
        onClick={onClick}
      >
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">
              {transaction.initiator_name}
            </span>
            <span className="text-muted-foreground">&rarr;</span>
            <span className="font-medium">
              {transaction.target_name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {categoryConfig?.label ?? transaction.category}
            </Badge>
            <span className="text-xs text-muted-foreground capitalize">
              {transaction.mode}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {new Date(transaction.created_at).toLocaleDateString()}
          </span>
          <StatusBadge
            status={transaction.status}
            statusMap={TRANSACTION_STATUS_CONFIG}
          />
        </div>
      </button>

      {/* Quick action buttons */}
      <div className="ml-2 flex shrink-0 items-center gap-1">
        {showAcceptDeny && (
          <>
            {onAccept && (
              <Button
                variant="default"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onAccept(transaction.id);
                }}
                disabled={isActioning}
              >
                Accept
              </Button>
            )}
            {onDeny && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmDenyOpen(true);
                  }}
                  disabled={isActioning}
                >
                  Deny
                </Button>
                <ConfirmActionDialog
                  open={confirmDenyOpen}
                  onOpenChange={setConfirmDenyOpen}
                  title="Deny Request"
                  description="Are you sure you want to deny this request?"
                  confirmLabel="Deny"
                  variant="destructive"
                  showReasonField
                  onConfirm={(reason) => {
                    setConfirmDenyOpen(false);
                    onDeny(transaction.id, reason);
                  }}
                  isLoading={isActioning}
                />
              </>
            )}
          </>
        )}

        {showCancel && (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                setConfirmCancelOpen(true);
              }}
              disabled={isCancelling}
            >
              Cancel
            </Button>
            <ConfirmActionDialog
              open={confirmCancelOpen}
              onOpenChange={setConfirmCancelOpen}
              title="Cancel Transaction"
              description="Are you sure you want to cancel this transaction? This action cannot be undone."
              confirmLabel="Cancel"
              variant="destructive"
              onConfirm={() => {
                setConfirmCancelOpen(false);
                onCancel!(transaction.id);
              }}
              isLoading={isCancelling}
            />
          </>
        )}
      </div>
    </div>
  );
}
