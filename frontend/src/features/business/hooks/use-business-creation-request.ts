"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { queryKeys } from "@/lib/query-keys";
import { useUser, useAuthStore } from "@/stores/auth-store";
import { fetchCurrentUserApi } from "@/features/users/api/users-api";
import { fetchPlatformAccountApi } from "@/features/platform/api/platform-api";
import {
  fetchTransactionsApi,
  checkRequestFormApi,
  submitRequestFormResponseApi,
  createRequestApi,
  type FormTemplateForTransaction,
} from "@/features/transactions/api/transactions-api";
import type { TransactionListItem } from "@/types/transactions";

// =============================================================================
// TYPES
// =============================================================================

export type BusinessCreationRequestStatus =
  | "approved"
  | "loading"
  | "error"
  | "has_pending"
  | "has_info_requested"
  | "in_cooldown"
  | "can_request";

export interface BusinessCreationRequestState {
  status: BusinessCreationRequestStatus;
  activeTransaction: TransactionListItem | null;
  cooldownDaysRemaining: number | null;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const COOLDOWN_DAYS = 30;
const ACTIVE_STATUSES = new Set(["pending", "pending_review"]);

// =============================================================================
// HOOK
// =============================================================================

export function useBusinessCreationRequest() {
  const user = useUser();
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  // Form dialog state
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [formMappingId, setFormMappingId] = useState<string | null>(null);
  const [formTemplateId, setFormTemplateId] = useState<string | null>(null);
  const [formTemplate, setFormTemplate] =
    useState<FormTemplateForTransaction | null>(null);
  const [formTemplateName, setFormTemplateName] = useState("");
  const [checking, setChecking] = useState(false);
  const [submittingForm, setSubmittingForm] = useState(false);
  const [submittingRequest, setSubmittingRequest] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const canCreateBusiness = user?.can_create_business ?? false;

  // Only fetch when user cannot create business
  const {
    data,
    isLoading: isQueryLoading,
    isError,
  } = useQuery({
    queryKey: queryKeys.transactions.businessCreationRequest(),
    queryFn: () =>
      fetchTransactionsApi({
        transaction_type: "business_creation_permission_request",
        role: "initiator",
        page_size: 5,
      }),
    enabled: !canCreateBusiness && !!user,
    staleTime: 30 * 1000,
    refetchOnWindowFocus: true,
  });

  const transactions = data?.results ?? [];

  // Derive state from server data
  const state: BusinessCreationRequestState = useMemo(() => {
    if (canCreateBusiness) {
      return { status: "approved", activeTransaction: null, cooldownDaysRemaining: null };
    }
    if (isQueryLoading) {
      return { status: "loading", activeTransaction: null, cooldownDaysRemaining: null };
    }
    if (isError) {
      return { status: "error", activeTransaction: null, cooldownDaysRemaining: null };
    }

    // Find active transaction (pending or pending_review)
    const active = transactions.find((t) => ACTIVE_STATUSES.has(t.status));
    if (active) {
      return { status: "has_pending", activeTransaction: active, cooldownDaysRemaining: null };
    }

    // Check for info_requested
    const infoRequested = transactions.find((t) => t.status === "info_requested");
    if (infoRequested) {
      return { status: "has_info_requested", activeTransaction: infoRequested, cooldownDaysRemaining: null };
    }

    // Check for accepted (will auto-refresh user)
    const accepted = transactions.find((t) => t.status === "accepted");
    if (accepted) {
      return { status: "approved", activeTransaction: null, cooldownDaysRemaining: null };
    }

    // Check cooldown from most recent denied (cooldown measured from creation, same as backend)
    const denied = transactions.find((t) => t.status === "denied");
    if (denied) {
      const createdAt = new Date(denied.created_at);
      const daysSince = Math.floor(
        (Date.now() - createdAt.getTime()) / (1000 * 60 * 60 * 24),
      );
      if (daysSince < COOLDOWN_DAYS) {
        return {
          status: "in_cooldown",
          activeTransaction: denied,
          cooldownDaysRemaining: COOLDOWN_DAYS - daysSince,
        };
      }
    }

    return { status: "can_request", activeTransaction: null, cooldownDaysRemaining: null };
  }, [canCreateBusiness, isQueryLoading, isError, transactions]);

  // Auto-refresh user when an accepted transaction is detected
  useEffect(() => {
    if (!canCreateBusiness && transactions.some((t) => t.status === "accepted")) {
      fetchCurrentUserApi()
        .then((freshUser) => setUser(freshUser))
        .catch(() => {
          // Silent — will pick up on next window focus
        });
    }
  }, [canCreateBusiness, transactions, setUser]);

  // Submit flow
  const handleRequestClick = useCallback(async () => {
    setChecking(true);
    try {
      const platform = await fetchPlatformAccountApi();

      const result = await checkRequestFormApi({
        transaction_type: "business_creation_permission_request",
        account_type: "platform",
        account_id: platform.id,
      });

      if (result.form_required && result.form_template) {
        setFormMappingId(result.form_mapping_id ?? null);
        setFormTemplateId(result.form_template_id ?? null);
        setFormTemplate(result.form_template);
        setFormTemplateName(result.form_template.name);
        setFormError(null);
        setFormDialogOpen(true);
      } else {
        // No form required — send directly
        await sendRequest(platform.id);
      }
    } catch {
      toast.error("Request failed", {
        description: "Platform is not configured or the form is not available.",
      });
    } finally {
      setChecking(false);
    }
  }, []);

  async function sendRequest(platformAccountId: string, formResponseId?: string) {
    setSubmittingRequest(true);
    try {
      await createRequestApi({
        transaction_type: "business_creation_permission_request",
        target_account_type: "platform",
        target_account_id: platformAccountId,
        form_response_id: formResponseId,
      });
      toast.success("Request sent", {
        description: "Your business creation request has been submitted for review.",
      });
      setFormDialogOpen(false);
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.businessCreationRequest(),
      });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "";
      if (msg.includes("duplicate") || msg.includes("conflict")) {
        toast.error("Request already exists", {
          description: "You already have an active request pending review.",
        });
      } else if (msg.includes("cooldown")) {
        toast.error("Cooldown active", {
          description: "Please wait before submitting another request.",
        });
      } else {
        toast.error("Request failed", {
          description: msg || "Could not submit request.",
        });
      }
    } finally {
      setSubmittingRequest(false);
    }
  }

  const handleFormSubmit = useCallback(
    async (formData: Record<string, unknown>) => {
      if (!formMappingId && !formTemplateId) return;
      setSubmittingForm(true);
      setFormError(null);

      try {
        const platform = await fetchPlatformAccountApi();
        const submitParams = formMappingId
          ? formMappingId
          : {
              form_template_id: formTemplateId!,
              account_type: "platform",
              account_id: platform.id,
            };
        const { form_response_id } = await submitRequestFormResponseApi(
          submitParams,
          formData,
        );
        await sendRequest(platform.id, form_response_id);
      } catch (err) {
        setFormError(
          err instanceof Error ? err.message : "Failed to submit form",
        );
      } finally {
        setSubmittingForm(false);
      }
    },
    [formMappingId, formTemplateId],
  );

  return {
    state,
    isLoading: isQueryLoading || checking || submittingRequest,
    checking,
    submittingForm,
    submittingRequest,
    formDialogOpen,
    setFormDialogOpen,
    formTemplate,
    formTemplateName,
    formError,
    handleRequestClick,
    handleFormSubmit,
  };
}
