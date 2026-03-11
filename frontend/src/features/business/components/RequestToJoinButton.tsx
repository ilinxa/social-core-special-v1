"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { queryKeys } from "@/lib/query-keys";
import { useIsAuthenticated } from "@/stores/auth-store";
import {
  useCreateRequest,
  useCancelTransaction,
} from "@/features/transactions/hooks/use-transaction-mutations";
import {
  checkRequestFormApi,
  submitRequestFormResponseApi,
  type FormTemplateForTransaction,
} from "@/features/transactions/api/transactions-api";
import { RequestWithFormDialog } from "@/features/transactions/components/RequestWithFormDialog";
import type { BusinessAccountWithRelationship } from "@/types/organization";

// Membership statuses that mean the user is (or will be) a member
const MEMBER_STATUSES = new Set(["active", "pending_approval", "suspended"]);

interface RequestToJoinButtonProps {
  business: BusinessAccountWithRelationship;
}

export function RequestToJoinButton({ business }: RequestToJoinButtonProps) {
  const isAuthenticated = useIsAuthenticated();
  const queryClient = useQueryClient();
  const createRequest = useCreateRequest();
  const cancelTransaction = useCancelTransaction();

  const [justSubmitted, setJustSubmitted] = useState(false);
  const [checking, setChecking] = useState(false);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [formMappingId, setFormMappingId] = useState<string | null>(null);
  const [formTemplate, setFormTemplate] =
    useState<FormTemplateForTransaction | null>(null);
  const [formTemplateName, setFormTemplateName] = useState("");
  const [submittingForm, setSubmittingForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Don't show if not authenticated
  if (!isAuthenticated) return null;

  // Don't show if requests not open
  if (!business.open_member_request) return null;

  const relationship = business._relationship;

  // Don't show if already a member (active, pending_approval, or suspended)
  if (relationship?.membership_status && MEMBER_STATUSES.has(relationship.membership_status)) {
    return null;
  }

  const activeTransaction = relationship?.active_transaction ?? null;

  function invalidateBusinessDetail() {
    queryClient.invalidateQueries({
      queryKey: queryKeys.business.detail(business.slug),
    });
  }

  function sendRequest(formResponseId?: string) {
    createRequest.mutate(
      {
        transaction_type: "business_membership_request",
        target_account_type: "business",
        target_account_id: business.id,
        form_response_id: formResponseId,
      },
      {
        onSuccess: () => {
          setJustSubmitted(true);
          toast.success("Request sent", {
            description: "Your membership request has been submitted.",
          });
          setFormDialogOpen(false);
          invalidateBusinessDetail();
        },
        onError: (error) => {
          const msg =
            error instanceof Error ? error.message : "";
          let description: string;
          if (msg.includes("maximum member limit")) {
            description =
              "This business has reached its member limit.";
          } else if (msg.includes("member_requests_closed") || msg.includes("not accepting")) {
            description =
              "This business is not accepting membership requests.";
          } else if (msg.includes("already an active member")) {
            description = "You are already a member of this business.";
          } else {
            description = msg || "Could not send request.";
          }
          toast.error("Request failed", { description });
        },
      },
    );
  }

  async function handleRequestClick() {
    setChecking(true);
    try {
      const result = await checkRequestFormApi({
        transaction_type: "business_membership_request",
        account_type: "business",
        account_id: business.id,
      });

      if (result.form_required && result.form_template && result.form_mapping_id) {
        setFormMappingId(result.form_mapping_id);
        setFormTemplate(result.form_template);
        setFormTemplateName(result.form_template.name);
        setFormError(null);
        setFormDialogOpen(true);
      } else {
        sendRequest();
      }
    } catch {
      sendRequest();
    } finally {
      setChecking(false);
    }
  }

  function handleCancelClick() {
    if (!activeTransaction) return;
    cancelTransaction.mutate(
      { transactionId: activeTransaction.id },
      {
        onSuccess: () => {
          setJustSubmitted(false);
          toast.success("Request cancelled", {
            description: "Your membership request has been cancelled.",
          });
          invalidateBusinessDetail();
        },
        onError: (error) => {
          toast.error("Cancel failed", {
            description:
              error instanceof Error
                ? error.message
                : "Could not cancel request.",
          });
        },
      },
    );
  }

  async function handleFormSubmit(formData: Record<string, unknown>) {
    if (!formMappingId) return;
    setSubmittingForm(true);
    setFormError(null);

    try {
      const { form_response_id } =
        await submitRequestFormResponseApi(formMappingId, formData);
      sendRequest(form_response_id);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to submit form",
      );
    } finally {
      setSubmittingForm(false);
    }
  }

  // Active invitation targeting this user — show informational message
  if (activeTransaction?.mode === "invitation") {
    return (
      <Button variant="secondary" disabled className="w-full sm:w-auto">
        Pending Invitation
      </Button>
    );
  }

  // Active request from this user — show Cancel button
  if (activeTransaction?.mode === "request" || justSubmitted) {
    const isCancelling = cancelTransaction.isPending;
    return (
      <Button
        variant="outline"
        onClick={handleCancelClick}
        disabled={isCancelling || !activeTransaction}
        className="w-full sm:w-auto"
      >
        {isCancelling ? "Cancelling..." : "Cancel Request"}
      </Button>
    );
  }

  // No active transaction — show Request to Join button
  const isLoading = checking || createRequest.isPending;

  return (
    <>
      <Button
        onClick={handleRequestClick}
        disabled={isLoading}
        className="w-full sm:w-auto"
      >
        {checking
          ? "Checking..."
          : createRequest.isPending
            ? "Sending..."
            : "Request to Join"}
      </Button>

      <RequestWithFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        formTemplateName={formTemplateName}
        formTemplate={formTemplate}
        onSubmit={handleFormSubmit}
        isSubmitting={submittingForm || createRequest.isPending}
        error={formError}
      />
    </>
  );
}
