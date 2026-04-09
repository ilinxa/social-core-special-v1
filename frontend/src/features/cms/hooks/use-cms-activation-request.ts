/**
 * CMS Activation Request Hook
 * =============================
 * State machine for CMS activation request flow.
 * Follows the pattern from use-business-creation-request.ts.
 *
 * States: loading → can_request | pending | has_info_requested | denied | in_cooldown | accepted
 */

"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";

// =============================================================================
// TYPES
// =============================================================================

export type CmsActivationStatus =
  | "loading"
  | "can_request"
  | "pending"
  | "has_info_requested"
  | "accepted"
  | "denied"
  | "in_cooldown";

const COOLDOWN_DAYS = 14;

type TransactionItem = {
  id: string;
  status: string;
  updated_at: string;
};

// =============================================================================
// HOOK
// =============================================================================

export function useCmsActivationRequest(businessSlug: string) {
  const queryClient = useQueryClient();

  // Query existing cms_activation_request transactions for this user
  const { data, isLoading } = useQuery({
    queryKey: [...queryKeys.cms.all, "activation-request", businessSlug],
    queryFn: async () => {
      const response = await apiClient.get<{
        results: TransactionItem[];
      }>("/transactions/", {
        params: {
          transaction_type: "cms_activation_request",
          role: "initiator",
          page_size: 5,
        },
      });
      return response.data.results;
    },
    staleTime: 60_000,
  });

  // Derive status from transactions
  const { status, activeTransaction } = useMemo(() => {
    if (isLoading || !data) {
      return { status: "loading" as const, activeTransaction: null };
    }

    // Find active transaction
    const pending = data.find(
      (t) => t.status === "pending" || t.status === "pending_review",
    );
    if (pending) {
      return { status: "pending" as const, activeTransaction: pending };
    }

    const infoRequested = data.find((t) => t.status === "info_requested");
    if (infoRequested) {
      return {
        status: "has_info_requested" as const,
        activeTransaction: infoRequested,
      };
    }

    const accepted = data.find((t) => t.status === "accepted");
    if (accepted) {
      return { status: "accepted" as const, activeTransaction: accepted };
    }

    const denied = data.find((t) => t.status === "denied");
    if (denied) {
      const deniedDate = new Date(denied.updated_at);
      const cooldownEnd = new Date(
        deniedDate.getTime() + COOLDOWN_DAYS * 24 * 60 * 60 * 1000,
      );
      if (new Date() < cooldownEnd) {
        return { status: "in_cooldown" as const, activeTransaction: denied };
      }
    }

    return { status: "can_request" as const, activeTransaction: null };
  }, [data, isLoading]);

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (payload?: { reason?: string }) => {
      const response = await apiClient.post("/transactions/request/", {
        transaction_type: "cms_activation_request",
        target_account_type: "platform",
        payload: {
          business_id: businessSlug, // The backend resolves this
          ...payload,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...queryKeys.cms.all, "activation-request", businessSlug],
      });
    },
  });

  return {
    status,
    activeTransaction,
    submit: (payload?: { reason?: string }) => submitMutation.mutate(payload),
    isSubmitting: submitMutation.isPending,
    isLoading,
  };
}
