"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import type { TransactionPermissions } from "@/types/transactions";

interface ActionButtonsProps {
  permissions: TransactionPermissions;
  onAccept?: () => void;
  onApprove?: () => void;
  onDeny?: (reason?: string) => void;
  onCancel?: () => void;
  onDismiss?: () => void;
  onRequestInfo?: () => void;
  onResubmit?: () => void;
  isLoading?: boolean;
}

export function ActionButtons({
  permissions,
  onAccept,
  onApprove,
  onDeny,
  onCancel,
  onDismiss,
  onRequestInfo,
  onResubmit,
  isLoading,
}: ActionButtonsProps) {
  const [denyOpen, setDenyOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  return (
    <div className="flex flex-wrap gap-2">
      <Can allowed={permissions.can_approve}>
        <Button size="sm" onClick={onApprove} disabled={isLoading}>
          Approve
        </Button>
      </Can>

      <Can allowed={permissions.can_accept}>
        <Button size="sm" onClick={onAccept} disabled={isLoading}>
          Accept
        </Button>
      </Can>

      <Can allowed={permissions.can_deny}>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => setDenyOpen(true)}
          disabled={isLoading}
        >
          Deny
        </Button>
        <ConfirmActionDialog
          open={denyOpen}
          onOpenChange={setDenyOpen}
          title="Deny Transaction"
          description="Are you sure you want to deny this transaction?"
          confirmLabel="Deny"
          variant="destructive"
          showReasonField
          reasonLabel="Reason"
          onConfirm={(reason) => {
            setDenyOpen(false);
            onDeny?.(reason);
          }}
          isLoading={isLoading}
        />
      </Can>

      <Can allowed={permissions.can_request_info}>
        <Button
          size="sm"
          variant="outline"
          onClick={onRequestInfo}
          disabled={isLoading}
        >
          Request Info
        </Button>
      </Can>

      <Can allowed={permissions.can_resubmit}>
        <Button
          size="sm"
          variant="outline"
          onClick={onResubmit}
          disabled={isLoading}
        >
          Resubmit
        </Button>
      </Can>

      <Can allowed={permissions.can_cancel}>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setCancelOpen(true)}
          disabled={isLoading}
        >
          Cancel
        </Button>
        <ConfirmActionDialog
          open={cancelOpen}
          onOpenChange={setCancelOpen}
          title="Cancel Transaction"
          description="Are you sure you want to cancel this transaction?"
          confirmLabel="Cancel Transaction"
          variant="destructive"
          onConfirm={() => {
            setCancelOpen(false);
            onCancel?.();
          }}
          isLoading={isLoading}
        />
      </Can>

      <Can allowed={permissions.can_dismiss}>
        <Button
          size="sm"
          variant="ghost"
          onClick={onDismiss}
          disabled={isLoading}
        >
          Dismiss
        </Button>
      </Can>
    </div>
  );
}
