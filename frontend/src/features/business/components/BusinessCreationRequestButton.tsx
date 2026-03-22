"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, Clock, ExternalLink, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { RequestWithFormDialog } from "@/features/transactions/components/RequestWithFormDialog";
import { useBusinessCreationRequest } from "@/features/business/hooks/use-business-creation-request";

export function BusinessCreationRequestButton() {
  const router = useRouter();
  const {
    state,
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
  } = useBusinessCreationRequest();

  // Already approved — parent (AccountSwitcher) shows "Create Business"
  if (state.status === "approved") return null;

  return (
    <>
      <Separator className="my-1" />

      {state.status === "loading" && (
        <div className="px-2 py-1.5">
          <Skeleton className="h-8 w-full" />
        </div>
      )}

      {state.status === "error" && (
        <button
          onClick={handleRequestClick}
          disabled={checking}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <Plus className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left">Request Business Access</span>
        </button>
      )}

      {state.status === "can_request" && (
        <button
          onClick={handleRequestClick}
          disabled={checking || submittingRequest}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <Plus className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left">
            {checking
              ? "Checking..."
              : submittingRequest
                ? "Sending..."
                : "Request Business Access"}
          </span>
        </button>
      )}

      {state.status === "has_pending" && (
        <div className="flex w-full items-center gap-2 px-2 py-1.5">
          <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="flex-1 text-left text-sm text-muted-foreground">
            Request Pending
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => {
              if (state.activeTransaction) {
                router.push(`/activity/${state.activeTransaction.id}`);
              }
            }}
          >
            View
            <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
        </div>
      )}

      {state.status === "has_info_requested" && (
        <div className="flex w-full items-center gap-2 px-2 py-1.5">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
          <span className="flex-1 text-left text-sm font-medium text-amber-700 dark:text-amber-400">
            Action Needed
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => {
              if (state.activeTransaction) {
                router.push(`/activity/${state.activeTransaction.id}`);
              }
            }}
          >
            Respond
            <ExternalLink className="ml-1 h-3 w-3" />
          </Button>
        </div>
      )}

      {state.status === "in_cooldown" && (
        <div className="px-2 py-1.5">
          <button
            disabled
            className="flex w-full items-center gap-2 rounded-md text-sm opacity-50 cursor-not-allowed"
          >
            <Plus className="h-4 w-4 shrink-0" />
            <span className="flex-1 text-left">Request Business Access</span>
          </button>
          <p className="mt-0.5 pl-6 text-xs text-muted-foreground">
            Available in {state.cooldownDaysRemaining} day
            {state.cooldownDaysRemaining !== 1 ? "s" : ""}
          </p>
        </div>
      )}

      <RequestWithFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        formTemplateName={formTemplateName}
        formTemplate={formTemplate}
        onSubmit={handleFormSubmit}
        isSubmitting={submittingForm || submittingRequest}
        error={formError}
      />
    </>
  );
}
