"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { ShieldCheck, Clock, AlertCircle, XCircle, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FormBuilder } from "@/features/forms/components/form-builder/FormBuilder";
import {
  fetchSystemTemplateApi,
  createResponseApi,
  submitResponseApi,
} from "@/features/forms/api/forms-api";
import { createRequestApi } from "@/features/transactions/api/transactions-api";
import type { FormField } from "@/types/forms";

// =============================================================================
// TYPES
// =============================================================================

type VerificationSectionProps = {
  verificationStatus: string;
  verificationStatusDisplay: string;
  accountId: string;
  isOwner: boolean;
};

// =============================================================================
// HELPERS
// =============================================================================

const STATUS_CONFIG: Record<
  string,
  { icon: React.ElementType; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
> = {
  unverified: { icon: AlertCircle, variant: "secondary" },
  pending: { icon: Clock, variant: "outline", className: "border-yellow-300 bg-yellow-50 text-yellow-800" },
  verified: { icon: ShieldCheck, variant: "default", className: "bg-green-100 text-green-800 border-green-300" },
  rejected: { icon: XCircle, variant: "destructive" },
  expired: { icon: Clock, variant: "secondary" },
};

const SYSTEM_FORM_SLUG = "system-business-verification";

// =============================================================================
// VERIFICATION REQUEST DIALOG
// =============================================================================

function VerificationRequestDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [fields, setFields] = useState<FormField[]>([]);
  const [templateId, setTemplateId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [values, setValues] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (!open) return;

    setLoading(true);
    fetchSystemTemplateApi(SYSTEM_FORM_SLUG)
      .then((template) => {
        setFields(template.fields);
        setTemplateId(template.id);
        setValues({});
      })
      .catch(() => {
        toast.error("Failed to load verification form.");
        onOpenChange(false);
      })
      .finally(() => setLoading(false));
  }, [open, onOpenChange]);

  const handleSubmit = useCallback(
    async (formValues: Record<string, unknown>) => {
      if (!templateId) return;
      setSubmitting(true);

      try {
        // 1. Create form response (DRAFT)
        const response = await createResponseApi(templateId, {
          data: formValues,
        });

        // 2. Submit the response
        await submitResponseApi(response.id);

        // 3. Create the verification transaction
        await createRequestApi({
          transaction_type: "business_verification_request",
          target_account_type: "platform",
          form_response_id: response.id,
          payload: {},
        });

        toast.success(
          "Verification request submitted. You will be notified when it's reviewed.",
        );
        onOpenChange(false);
        onSuccess();
      } catch {
        toast.error("Failed to submit verification request. Please try again.");
      } finally {
        setSubmitting(false);
      }
    },
    [templateId, onOpenChange, onSuccess],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Request Business Verification</DialogTitle>
          <DialogDescription>
            Fill out the verification form below. A platform administrator will
            review your request.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <FormBuilder
            fields={fields}
            mode="fill"
            values={values}
            onValuesChange={setValues}
            onSubmit={handleSubmit}
            submitLabel={submitting ? "Submitting..." : "Submit Request"}
            submitDisabled={submitting}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// VERIFICATION SECTION
// =============================================================================

export function VerificationSection({
  verificationStatus,
  verificationStatusDisplay,
  accountId,
  isOwner,
}: VerificationSectionProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  const config = STATUS_CONFIG[verificationStatus] ?? STATUS_CONFIG.unverified;
  const Icon = config.icon;
  const canRequest =
    isOwner && (verificationStatus === "unverified" || verificationStatus === "rejected" || verificationStatus === "expired");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Verification</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Icon className="h-5 w-5 text-muted-foreground" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <p className="font-medium">Verification Status</p>
                <Badge variant={config.variant} className={config.className}>
                  {verificationStatusDisplay}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {verificationStatus === "unverified" &&
                  "Verify your business to build trust with members and customers."}
                {verificationStatus === "pending" &&
                  "Your verification request is being reviewed."}
                {verificationStatus === "verified" &&
                  "Your business has been verified."}
                {verificationStatus === "rejected" &&
                  "Your verification request was rejected. You may resubmit after the cooldown period."}
                {verificationStatus === "expired" &&
                  "Your verification has expired. Please submit a new request."}
              </p>
            </div>
          </div>

          {canRequest && (
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              Request Verification
            </Button>
          )}
        </div>

        <VerificationRequestDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onSuccess={() => {
            // Refresh happens via TQ invalidation in the mutation
          }}
        />
      </CardContent>
    </Card>
  );
}
