"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Archive,
  ArrowLeft,
  Building2,
  CheckCircle,
  RotateCcw,
  Users,
} from "lucide-react";
import { toast } from "sonner";

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
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useGovernanceBusiness } from "@/features/governance/hooks/use-governance-queries";
import {
  useArchiveBusiness,
  useReactivateBusiness,
  useSuspendBusiness,
} from "@/features/governance/hooks/use-governance-mutations";

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "suspended":
      return "destructive";
    case "archived":
      return "secondary";
    case "pending":
      return "outline";
    default:
      return "secondary";
  }
}

interface GovernanceBusinessDetailPageProps {
  businessId: string;
}

export function GovernanceBusinessDetailPage({
  businessId,
}: GovernanceBusinessDetailPageProps) {
  const router = useRouter();
  const { data: business, isLoading } = useGovernanceBusiness(businessId);

  const [suspendOpen, setSuspendOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [reactivateOpen, setReactivateOpen] = useState(false);

  const suspendMutation = useSuspendBusiness();
  const reactivateMutation = useReactivateBusiness();
  const archiveMutation = useArchiveBusiness();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-32 w-full rounded-lg" />
      </div>
    );
  }

  if (!business) {
    return (
      <div className="text-muted-foreground py-12 text-center">
        Business not found.
      </div>
    );
  }

  const permissions = business._permissions;

  function handleSuspend(reason?: string) {
    if (!reason) return;
    suspendMutation.mutate(
      { id: businessId, reason },
      {
        onSuccess: () => {
          setSuspendOpen(false);
          toast.success("Business suspended");
        },
        onError: () => toast.error("Failed to suspend business"),
      },
    );
  }

  function handleReactivate() {
    reactivateMutation.mutate(
      { id: businessId },
      {
        onSuccess: () => {
          setReactivateOpen(false);
          toast.success("Business reactivated");
        },
        onError: () => toast.error("Failed to reactivate business"),
      },
    );
  }

  function handleArchive() {
    archiveMutation.mutate(
      { id: businessId },
      {
        onSuccess: () => {
          setArchiveOpen(false);
          toast.success("Business archived");
        },
        onError: () => toast.error("Failed to archive business"),
      },
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-3">
          <Building2 className="text-muted-foreground h-6 w-6" />
          <h1 className="text-2xl font-bold">{business.legal_name}</h1>
          <Badge variant={statusBadgeVariant(business.status)}>
            {business.status_display}
          </Badge>
          {business.verification_status === "verified" && (
            <Badge variant="outline">
              <CheckCircle className="mr-1 h-3 w-3" />
              Verified
            </Badge>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <Can allowed={permissions.can_suspend && business.status === "active"}>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setSuspendOpen(true)}
          >
            <AlertTriangle className="mr-1 h-4 w-4" />
            Suspend
          </Button>
        </Can>
        <Can
          allowed={permissions.can_suspend && business.status === "suspended"}
        >
          <Button variant="default" size="sm" onClick={() => setReactivateOpen(true)}>
            <RotateCcw className="mr-1 h-4 w-4" />
            Reactivate
          </Button>
        </Can>
        <Can
          allowed={
            permissions.can_archive &&
            (business.status === "active" || business.status === "suspended")
          }
        >
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setArchiveOpen(true)}
          >
            <Archive className="mr-1 h-4 w-4" />
            Archive
          </Button>
        </Can>
      </div>

      {/* Business info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Business Information</CardTitle>
            <CardDescription>Core details and classification</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Slug" value={business.slug} />
            <InfoRow label="Type" value={business.business_type_display} />
            <InfoRow label="Country" value={business.country} />
            {business.city && <InfoRow label="City" value={business.city} />}
            <InfoRow
              label="Platform Branch"
              value={business.is_platform_branch ? "Yes" : "No"}
            />
            <InfoRow
              label="Created"
              value={new Date(business.created_at).toLocaleDateString()}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status & Members</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow label="Status" value={business.status_display} />
            <InfoRow
              label="Verification"
              value={business.verification_status_display}
            />
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Members</span>
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {business.member_count} / {business.max_members || "Unlimited"}
              </span>
            </div>
            {business.owner_email && (
              <InfoRow label="Owner" value={business.owner_email} />
            )}
            {business.owner_name && (
              <InfoRow label="Owner Name" value={business.owner_name} />
            )}
          </CardContent>
        </Card>

        <Can allowed={permissions.can_view_legal_info}>
          <Card>
            <CardHeader>
              <CardTitle>Legal Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow
                label="Registration #"
                value={business.registration_number || "Not provided"}
              />
              <InfoRow
                label="Tax ID"
                value={business.tax_id || "Not provided"}
              />
              <InfoRow
                label="Legal Address"
                value={business.legal_address || "Not provided"}
              />
            </CardContent>
          </Card>
        </Can>

        {business.profile && (
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow
                label="Display Name"
                value={business.profile.display_name}
              />
              {business.profile.tagline && (
                <InfoRow label="Tagline" value={business.profile.tagline} />
              )}
              {business.profile.website && (
                <InfoRow label="Website" value={business.profile.website} />
              )}
              {business.profile.industry && (
                <InfoRow label="Industry" value={business.profile.industry} />
              )}
              <InfoRow
                label="Public"
                value={business.profile.is_public ? "Yes" : "No"}
              />
            </CardContent>
          </Card>
        )}
      </div>

      {/* Dialogs */}
      <ConfirmActionDialog
        open={suspendOpen}
        onOpenChange={setSuspendOpen}
        title="Suspend Business"
        description={`Suspend "${business.legal_name}"? Members will lose access until reactivated.`}
        confirmLabel="Suspend"
        variant="destructive"
        showReasonField
        reasonRequired
        reasonLabel="Suspension reason"
        onConfirm={handleSuspend}
        isLoading={suspendMutation.isPending}
      />
      <ConfirmActionDialog
        open={reactivateOpen}
        onOpenChange={setReactivateOpen}
        title="Reactivate Business"
        description={`Reactivate "${business.legal_name}"? Members will regain access.`}
        confirmLabel="Reactivate"
        onConfirm={handleReactivate}
        isLoading={reactivateMutation.isPending}
      />
      <ConfirmActionDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title="Archive Business"
        description={`Archive "${business.legal_name}"? This is a permanent action — archived businesses cannot be reactivated.`}
        confirmLabel="Archive"
        variant="destructive"
        onConfirm={handleArchive}
        isLoading={archiveMutation.isPending}
      />
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[60%] truncate text-right">{value}</span>
    </div>
  );
}
