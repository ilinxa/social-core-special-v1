/**
 * CMS Activation Page
 * ====================
 * Shown when a business doesn't have CMS enabled.
 * Renders different states based on activation request status.
 *
 * States:
 * - can_request → "Request CMS Access" button
 * - pending → "Your request is pending"
 * - in_cooldown → "Request denied, try again later"
 * - gate disabled → "Contact platform admin"
 */

"use client";

import { Clock, FileText, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCmsFeatureEnabled } from "@/features/cms/hooks/use-cms-feature-gate";
import { useCmsActivationRequest } from "@/features/cms/hooks/use-cms-activation-request";

interface CmsActivationPageProps {
  businessSlug: string;
}

export function CmsActivationPage({ businessSlug }: CmsActivationPageProps) {
  const activationRequestEnabled = useCmsFeatureEnabled("activation_request");
  const { status, submit, isSubmitting, isLoading } =
    useCmsActivationRequest(businessSlug);

  if (isLoading) {
    return (
      <div className="flex min-h-100 items-center justify-center p-8">
        <Skeleton className="h-60 w-96 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="flex min-h-100 items-center justify-center p-8">
      <Card className="max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            {status === "pending" ? (
              <Clock className="h-6 w-6 text-blue-500" />
            ) : status === "in_cooldown" ? (
              <XCircle className="h-6 w-6 text-yellow-500" />
            ) : (
              <FileText className="h-6 w-6 text-muted-foreground" />
            )}
          </div>

          {status === "pending" && (
            <>
              <CardTitle>Request Pending</CardTitle>
              <CardDescription>
                Your CMS activation request is being reviewed by the platform
                team.
              </CardDescription>
            </>
          )}

          {status === "has_info_requested" && (
            <>
              <CardTitle>Action Needed</CardTitle>
              <CardDescription>
                The platform team has requested more information about your CMS
                activation request.
              </CardDescription>
            </>
          )}

          {status === "in_cooldown" && (
            <>
              <CardTitle>Request Denied</CardTitle>
              <CardDescription>
                Your previous request was denied. You can submit a new request
                after the cooldown period.
              </CardDescription>
            </>
          )}

          {status === "can_request" && (
            <>
              <CardTitle>CMS Not Enabled</CardTitle>
              <CardDescription>
                {activationRequestEnabled
                  ? "Request CMS access to start creating and managing content for your business."
                  : "CMS is not available for this business. Contact a platform administrator to enable it."}
              </CardDescription>
            </>
          )}
        </CardHeader>

        <CardContent className="text-center">
          {status === "pending" && (
            <Badge variant="outline" className="text-blue-600">
              Awaiting Review
            </Badge>
          )}

          {status === "has_info_requested" && (
            <Badge variant="outline" className="text-amber-600">
              Information Requested
            </Badge>
          )}

          {status === "can_request" && activationRequestEnabled && (
            <Button onClick={() => submit()} disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Request CMS Access"}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
