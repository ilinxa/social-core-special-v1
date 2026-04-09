"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NotificationPreferencesPanel } from "@/features/notifications/components/NotificationPreferencesPanel";
import { useNotificationSystemEnabled } from "@/stores/notification-store";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { OwnershipTransferDialog } from "@/features/members/components/OwnershipTransferDialog";
import { useLeaveMember } from "@/features/members/hooks/use-member-mutations";
import {
  useArchiveBusiness,
  useDeleteBusiness,
} from "@/features/business/hooks/use-business-mutations";
import { useBusiness } from "@/features/business/hooks/use-business-queries";
import { VerificationSection } from "@/features/business/components/VerificationSection";
import {
  useBusinessMemberships,
  usePlatformMembership,
} from "@/stores/membership-store";
import { useMembershipStore } from "@/stores/membership-store";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";
import type { AccountType } from "@/types/rbac";

// =============================================================================
// INNER COMPONENT
// =============================================================================

interface SettingsPageInnerProps {
  accountType: AccountType;
  slug: string;
  accountId: string;
  isOwner: boolean;
  verificationStatus?: string;
  verificationStatusDisplay?: string;
}

function SettingsPageInner({
  accountType,
  slug,
  accountId,
  isOwner,
  verificationStatus,
  verificationStatusDisplay,
}: SettingsPageInnerProps) {
  const router = useRouter();
  const notificationsEnabled = useNotificationSystemEnabled();
  const [transferOpen, setTransferOpen] = useState(false);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const leaveMutation = useLeaveMember(accountType, slug);
  const archiveMutation = useArchiveBusiness(slug);
  const deleteMutation = useDeleteBusiness(slug);

  const accountLabel = accountType === "business" ? "business" : "platform";

  const handleLeave = () => {
    leaveMutation.mutate(undefined, {
      onSuccess: async () => {
        toast.success(`You have left this ${accountLabel}.`);
        setLeaveOpen(false);
        // Refresh memberships in Zustand store
        try {
          const memberships = await fetchMyMembershipsApi();
          useMembershipStore.getState().setMemberships(memberships);
        } catch {
          // Best effort — guard will redirect anyway
        }
        router.push("/home");
      },
      onError: () => {
        toast.error(`Failed to leave this ${accountLabel}. Please try again.`);
      },
    });
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      {/* General settings placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">General</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            General account settings will be available here.
          </p>
        </CardContent>
      </Card>

      {/* Notification preferences */}
      {notificationsEnabled && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Notification Preferences</h2>
          <NotificationPreferencesPanel />
        </div>
      )}

      {/* Verification — business accounts only */}
      {accountType === "business" && verificationStatus && (
        <VerificationSection
          verificationStatus={verificationStatus}
          verificationStatusDisplay={verificationStatusDisplay ?? "Unverified"}
          accountId={accountId}
          isOwner={isOwner}
        />
      )}

      {/* Leave — non-owner members only */}
      {!isOwner && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-base text-destructive">
              Membership
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between rounded-md border border-destructive/30 p-4">
              <div className="space-y-1">
                <p className="font-medium">Leave {accountLabel}</p>
                <p className="text-sm text-muted-foreground">
                  You will lose access to this {accountLabel} and its resources.
                  You can be re-invited later.
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setLeaveOpen(true)}
              >
                Leave
              </Button>
            </div>

            <ConfirmActionDialog
              open={leaveOpen}
              onOpenChange={setLeaveOpen}
              title={`Leave ${accountLabel}?`}
              description={`Are you sure you want to leave this ${accountLabel}? You will lose access to all its resources immediately.`}
              confirmLabel="Leave"
              variant="destructive"
              onConfirm={handleLeave}
              isLoading={leaveMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      {/* Danger Zone — owner only */}
      {isOwner && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-base text-destructive">
              Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-md border border-destructive/30 p-4">
              <div className="space-y-1">
                <p className="font-medium">Transfer Ownership</p>
                <p className="text-sm text-muted-foreground">
                  Transfer this account to another member. You will be demoted
                  to Base Member.
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setTransferOpen(true)}
              >
                Transfer
              </Button>
            </div>

            <OwnershipTransferDialog
              open={transferOpen}
              onOpenChange={setTransferOpen}
              accountType={accountType}
              slug={slug}
              accountId={accountId}
            />

            {/* Archive — business only */}
            {accountType === "business" && (
              <>
                <div className="flex items-center justify-between rounded-md border border-destructive/30 p-4">
                  <div className="space-y-1">
                    <p className="font-medium">Archive Business</p>
                    <p className="text-sm text-muted-foreground">
                      Archive this business account. It will become read-only
                      and hidden from public view.
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setArchiveOpen(true)}
                  >
                    Archive
                  </Button>
                </div>

                <ConfirmActionDialog
                  open={archiveOpen}
                  onOpenChange={setArchiveOpen}
                  title="Archive this business?"
                  description="Archiving will make this business read-only and hide it from public view. You can contact support to restore it later."
                  confirmLabel="Archive"
                  variant="destructive"
                  onConfirm={() => {
                    archiveMutation.mutate(undefined, {
                      onSuccess: async () => {
                        toast.success("Business archived successfully.");
                        setArchiveOpen(false);
                        try {
                          const memberships = await fetchMyMembershipsApi();
                          useMembershipStore.getState().setMemberships(memberships);
                        } catch {
                          // Best effort
                        }
                        router.push("/home");
                      },
                      onError: () => {
                        toast.error("Failed to archive business. Please try again.");
                      },
                    });
                  }}
                  isLoading={archiveMutation.isPending}
                />
              </>
            )}

            {/* Delete */}
            {accountType === "business" && (
              <>
                <div className="flex items-center justify-between rounded-md border border-destructive/30 p-4">
                  <div className="space-y-1">
                    <p className="font-medium">Delete Business</p>
                    <p className="text-sm text-muted-foreground">
                      Permanently delete this business account and all its
                      data. This action cannot be undone.
                    </p>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setDeleteOpen(true)}
                  >
                    Delete
                  </Button>
                </div>

                <ConfirmActionDialog
                  open={deleteOpen}
                  onOpenChange={setDeleteOpen}
                  title="Delete this business permanently?"
                  description="This will permanently delete this business account and all associated data including members, roles, transactions, and forms. This action cannot be undone."
                  confirmLabel="Delete Permanently"
                  variant="destructive"
                  onConfirm={() => {
                    deleteMutation.mutate(undefined, {
                      onSuccess: async () => {
                        toast.success("Business deleted.");
                        setDeleteOpen(false);
                        try {
                          const memberships = await fetchMyMembershipsApi();
                          useMembershipStore.getState().setMemberships(memberships);
                        } catch {
                          // Best effort
                        }
                        router.push("/home");
                      },
                      onError: () => {
                        toast.error("Failed to delete business. Please try again.");
                      },
                    });
                  }}
                  isLoading={deleteMutation.isPending}
                />
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// BUSINESS WRAPPER
// =============================================================================

export function BusinessSettingsPage() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";
  const isOwner = myMembership?.is_owner ?? false;
  const { data: business } = useBusiness(slug);

  return (
    <SettingsPageInner
      accountType="business"
      slug={slug}
      accountId={accountId}
      isOwner={isOwner}
      verificationStatus={business?.verification_status}
      verificationStatusDisplay={business?.verification_status_display}
    />
  );
}

// =============================================================================
// PLATFORM WRAPPER
// =============================================================================

export function PlatformSettingsPage() {
  const myMembership = usePlatformMembership();
  const accountId = myMembership?.account_id ?? "";
  const isOwner = myMembership?.is_owner ?? false;

  return (
    <SettingsPageInner
      accountType="platform"
      slug="platform"
      accountId={accountId}
      isOwner={isOwner}
    />
  );
}
