"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Can } from "@/components/common/Can";
import { ActionButtons } from "./ActionButtons";
import { AcceptWithFormDialog } from "./AcceptWithFormDialog";
import { RequestChangesDialog } from "./RequestChangesDialog";
import { TransactionFormPanel } from "./TransactionFormPanel";
import { ResubmitFormPanel } from "./ResubmitFormPanel";
import { TransactionTimeline } from "./TransactionTimeline";
import {
  TRANSACTION_STATUS_CONFIG,
} from "@/features/transactions/constants/transaction-statuses";
import {
  useTransactionDetail,
} from "@/features/transactions/hooks/use-transaction-queries";
import {
  useAcceptTransaction,
  useDenyTransaction,
  useCancelTransaction,
  useDismissTransaction,
  useRequestInfo,
  useResubmitTransaction,
  useApproveTransaction,
} from "@/features/transactions/hooks/use-transaction-mutations";
import {
  fetchRequiredFormApi,
} from "@/features/transactions/api/transactions-api";
import { queryKeys } from "@/lib/query-keys";
import type { FormField } from "@/types/forms";

interface TransactionDetailPageProps {
  transactionId: string;
  basePath: string;
}

export function TransactionDetailPage({
  transactionId,
  basePath,
}: TransactionDetailPageProps) {
  const router = useRouter();
  const { data: txn, isLoading } = useTransactionDetail(transactionId);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [requestChangesOpen, setRequestChangesOpen] = useState(false);

  const accept = useAcceptTransaction();
  const approve = useApproveTransaction();
  const deny = useDenyTransaction();
  const cancel = useCancelTransaction();
  const dismiss = useDismissTransaction();
  const requestInfo = useRequestInfo();
  const resubmit = useResubmitTransaction();

  // Fetch form template fields for the RequestChangesDialog
  const { data: formTemplateData } = useQuery({
    queryKey: queryKeys.transactions.requiredForm(transactionId),
    queryFn: () => fetchRequiredFormApi(transactionId),
    enabled: !!txn?.form_response,
  });

  const formFields: FormField[] = useMemo(() => {
    const raw = formTemplateData?.form_template?.fields ?? [];
    return raw.map((f) => ({
      id: f.id,
      field_key: f.field_key,
      field_type: f.field_type as FormField["field_type"],
      label: f.label,
      description: f.description,
      placeholder: f.placeholder,
      order: f.order,
      step_tag: "",
      section_tag: "",
      options: f.options,
      validation_rules: f.validation_rules,
      ui_config: {},
      default_value: null,
      is_required: f.is_required,
      is_indexed: false,
      is_hidden: f.is_hidden,
      is_readonly: false,
    }));
  }, [formTemplateData]);

  const anyActionLoading =
    accept.isPending ||
    approve.isPending ||
    deny.isPending ||
    cancel.isPending ||
    dismiss.isPending ||
    requestInfo.isPending ||
    resubmit.isPending;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!txn) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">Transaction not found.</p>
        <Button variant="outline" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  // Check if a form needs to be filled before accepting
  const needsFormBeforeAccept =
    txn.form_mapping && !txn.form_response_id;

  const isInfoRequested = txn.status === "info_requested";
  const isPendingReview = txn.status === "pending_review";
  const hasFormResponse = !!txn.form_response;

  function handleAccept() {
    if (!txn) return;
    if (needsFormBeforeAccept) {
      setFormDialogOpen(true);
    } else {
      accept.mutate(
        { transactionId: txn.id },
        {
          onSuccess: () => toast.success("Transaction accepted"),
          onError: () => toast.error("Failed to accept transaction"),
        },
      );
    }
  }

  function handleAcceptWithForm(formResponseId: string) {
    if (!txn) return;
    setFormDialogOpen(false);
    accept.mutate(
      {
        transactionId: txn.id,
        data: { form_response_id: formResponseId },
      },
      {
        onSuccess: () => toast.success("Transaction accepted"),
        onError: () => toast.error("Failed to accept transaction"),
      },
    );
  }

  function handleRequestChanges(message: string, requestedFields: string[]) {
    if (!txn) return;
    setRequestChangesOpen(false);
    requestInfo.mutate(
      {
        transactionId: txn.id,
        data: {
          message,
          requested_fields: requestedFields.length > 0 ? requestedFields : undefined,
        },
      },
      {
        onSuccess: () => toast.success("Changes requested — submitter will be notified"),
        onError: () => toast.error("Failed to request changes"),
      },
    );
  }

  function handleApprove() {
    if (!txn) return;
    approve.mutate(
      { transactionId: txn.id },
      {
        onSuccess: () => toast.success("Submission approved — member is now active"),
        onError: () => toast.error("Failed to approve"),
      },
    );
  }

  function handleResubmit() {
    if (!txn) return;
    resubmit.mutate(
      { transactionId: txn.id },
      {
        onSuccess: () => toast.success("Response resubmitted for review"),
        onError: () => toast.error("Failed to resubmit"),
      },
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              Transaction Detail
            </h1>
            <StatusBadge
              status={txn.status}
              statusMap={TRANSACTION_STATUS_CONFIG}
            />
          </div>
          <p className="text-sm text-muted-foreground">
            {txn.transaction_type.replace(/_/g, " ")} &middot;{" "}
            <span className="capitalize">{txn.mode}</span>
          </p>
        </div>
        <Button variant="outline" onClick={() => router.back()}>
          Back
        </Button>
      </div>

      {/* Form requirement notice (form not yet submitted) */}
      {needsFormBeforeAccept && txn._permissions.can_accept && (
        <Card className="border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950">
          <CardContent className="py-3">
            <p className="text-sm">
              This transaction requires you to fill out the form
              &quot;{txn.form_mapping!.form_template_name}&quot; before accepting.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Pending Review banner (for reviewer — form submitted, needs approval) */}
      {isPendingReview && txn._permissions.can_approve && (
        <Card className="border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950">
          <CardContent className="py-3">
            <p className="text-sm">
              The invitee has submitted their form. Review the response below,
              then approve to activate their membership, request changes, or deny.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Pending Review banner (for submitter — waiting for business review) */}
      {isPendingReview && !txn._permissions.can_approve && (
        <Card className="border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950">
          <CardContent className="py-3">
            <p className="text-sm">
              Your submission is being reviewed. You will be notified once the
              business approves or requests changes.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <ActionButtons
        permissions={{
          ...txn._permissions,
          // Override request_info — use our dialog instead of the plain button
          can_request_info: false,
        }}
        onAccept={handleAccept}
        onApprove={handleApprove}
        onDeny={(reason) =>
          deny.mutate(
            {
              transactionId: txn.id,
              data: reason ? { reason } : undefined,
            },
            {
              onSuccess: () => toast.success("Transaction denied"),
              onError: () => toast.error("Failed to deny transaction"),
            },
          )
        }
        onCancel={() =>
          cancel.mutate(
            { transactionId: txn.id },
            {
              onSuccess: () => toast.success("Transaction cancelled"),
              onError: () => toast.error("Failed to cancel transaction"),
            },
          )
        }
        onDismiss={() =>
          dismiss.mutate(
            { transactionId: txn.id },
            {
              onSuccess: () => toast.success("Transaction dismissed"),
              onError: () => toast.error("Failed to dismiss transaction"),
            },
          )
        }
        onResubmit={handleResubmit}
        isLoading={anyActionLoading}
      />

      {/* Request Changes button (separate from ActionButtons so we can use our dialog) */}
      <Can allowed={txn._permissions.can_request_info && hasFormResponse}>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setRequestChangesOpen(true)}
          disabled={anyActionLoading}
        >
          Request Changes
        </Button>
      </Can>

      {/* Details Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Parties</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Initiator</p>
              <div className="flex items-center gap-2">
                <Avatar size="sm">
                  <AvatarImage src={txn.initiator_avatar_url ?? undefined} alt={txn.initiator_name} />
                  <AvatarFallback>{txn.initiator_name?.charAt(0)?.toUpperCase() || "?"}</AvatarFallback>
                </Avatar>
                <p className="font-medium">{txn.initiator_name || txn.initiator_id}</p>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Target</p>
              <div className="flex items-center gap-2">
                {txn.target_type !== "account" && (
                  <Avatar size="sm">
                    <AvatarImage src={txn.target_avatar_url ?? undefined} alt={txn.target_name} />
                    <AvatarFallback>{txn.target_name?.charAt(0)?.toUpperCase() || "?"}</AvatarFallback>
                  </Avatar>
                )}
                <p className="font-medium">{txn.target_name || txn.target_id}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="text-sm">
                {new Date(txn.created_at).toLocaleString()}
              </p>
            </div>
            {txn.expires_at && (
              <div>
                <p className="text-sm text-muted-foreground">Expires</p>
                <p className="text-sm">
                  {new Date(txn.expires_at).toLocaleString()}
                </p>
              </div>
            )}
            {txn.resolved_at && (
              <div>
                <p className="text-sm text-muted-foreground">Resolved</p>
                <p className="text-sm">
                  {new Date(txn.resolved_at).toLocaleString()}
                </p>
              </div>
            )}
            {txn.resolution_reason && (
              <div>
                <p className="text-sm text-muted-foreground">Resolution Reason</p>
                <p className="text-sm">{txn.resolution_reason}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Requested banner (for reviewer — shows what was requested) */}
      {isInfoRequested && !txn._permissions.can_resubmit && txn.info_requested_message && (
        <Card className="border-amber-200 dark:border-amber-800">
          <CardHeader>
            <CardTitle className="text-base">Changes Requested</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm">{txn.info_requested_message}</p>
            {txn.info_requested_fields && txn.info_requested_fields.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {txn.info_requested_fields.map((field) => (
                  <Badge key={field} variant="secondary">
                    {field}
                  </Badge>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Waiting for the submitter to update and resubmit.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Resubmit panel (for initiator — editable form when info_requested) */}
      {isInfoRequested && txn._permissions.can_resubmit && hasFormResponse && (
        <ResubmitFormPanel
          transactionId={txn.id}
          formResponse={txn.form_response!}
          infoRequestedMessage={txn.info_requested_message}
          infoRequestedFields={txn.info_requested_fields}
          onResubmit={handleResubmit}
          isResubmitting={resubmit.isPending}
        />
      )}

      {/* Form response viewer (for reviewer — read-only table of submitted data) */}
      {!isInfoRequested && hasFormResponse && txn._permissions.can_view_form && (
        <TransactionFormPanel
          formResponse={txn.form_response!}
          fields={formFields}
          infoRequestedFields={txn.info_requested_fields}
        />
      )}

      {/* Timeline */}
      <TransactionTimeline logs={txn.logs} />

      {/* Accept with Form Dialog */}
      {txn.form_mapping && (
        <AcceptWithFormDialog
          open={formDialogOpen}
          onOpenChange={setFormDialogOpen}
          transactionId={txn.id}
          formTemplateName={txn.form_mapping.form_template_name}
          onAcceptWithForm={handleAcceptWithForm}
          isAccepting={accept.isPending}
        />
      )}

      {/* Request Changes Dialog */}
      <RequestChangesDialog
        open={requestChangesOpen}
        onOpenChange={setRequestChangesOpen}
        fields={formFields}
        onSubmit={handleRequestChanges}
        isLoading={requestInfo.isPending}
      />
    </div>
  );
}
