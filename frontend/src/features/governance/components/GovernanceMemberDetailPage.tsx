"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Ban,
  RotateCcw,
  UserMinus,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { useGovernanceMember } from "@/features/governance/hooks/use-governance-queries";
import { useGovernanceMemberAction } from "@/features/governance/hooks/use-governance-mutations";

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "active":
      return "default";
    case "suspended":
      return "outline";
    case "banned":
      return "destructive";
    case "removed":
      return "secondary";
    default:
      return "secondary";
  }
}

interface GovernanceMemberDetailPageProps {
  memberId: string;
}

export function GovernanceMemberDetailPage({
  memberId,
}: GovernanceMemberDetailPageProps) {
  const router = useRouter();
  const { data: member, isLoading } = useGovernanceMember(memberId);

  const [suspendOpen, setSuspendOpen] = useState(false);
  const [banOpen, setBanOpen] = useState(false);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [reactivateOpen, setReactivateOpen] = useState(false);

  const actionMutation = useGovernanceMemberAction();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
    );
  }

  if (!member) {
    return (
      <div className="text-muted-foreground py-12 text-center">
        Member not found.
      </div>
    );
  }

  const permissions = member._permissions;
  const initials = member.user.display_name
    ? member.user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : member.user.email[0].toUpperCase();

  function handleAction(action: string, reason?: string) {
    actionMutation.mutate(
      { id: memberId, action, reason },
      {
        onSuccess: () => {
          toast.success(
            `Member ${action === "reactivate" ? "reactivated" : action + "ed"} successfully`,
          );
          setSuspendOpen(false);
          setBanOpen(false);
          setRemoveOpen(false);
          setReactivateOpen(false);
        },
        onError: () => {
          toast.error(`Failed to ${action} member`);
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/gconsole/members")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Member Detail</h1>
      </div>

      {/* Member info card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14">
              <AvatarImage
                src={member.user.avatar_url ?? undefined}
                alt={member.user.display_name}
              />
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="flex items-center gap-2">
                {member.user.display_name || member.user.username}
                <Badge variant={statusBadgeVariant(member.status)}>
                  {member.status}
                </Badge>
                {member.is_owner && <Badge variant="outline">Owner</Badge>}
              </CardTitle>
              <CardDescription>{member.user.email}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground text-sm">Account</dt>
              <dd className="font-medium">
                {member.account_name}
                {member.account_slug ? ` (${member.account_slug})` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-sm">Account Type</dt>
              <dd className="font-medium capitalize">{member.account_type}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-sm">Role</dt>
              <dd className="font-medium">
                {member.role_name} (level {member.role_level})
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground text-sm">Joined</dt>
              <dd className="font-medium">
                {new Date(member.joined_at).toLocaleDateString()}
              </dd>
            </div>
            {member.status_reason && (
              <div className="sm:col-span-2">
                <dt className="text-muted-foreground text-sm">
                  Status Reason
                </dt>
                <dd className="font-medium">{member.status_reason}</dd>
              </div>
            )}
            {member.status_changed_at && (
              <div>
                <dt className="text-muted-foreground text-sm">
                  Status Changed
                </dt>
                <dd className="font-medium">
                  {new Date(member.status_changed_at).toLocaleString()}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Can
            allowed={permissions.can_suspend && member.status === "active"}
          >
            <Button
              variant="outline"
              onClick={() => setSuspendOpen(true)}
              disabled={actionMutation.isPending}
            >
              <AlertTriangle className="mr-2 h-4 w-4" />
              Suspend
            </Button>
          </Can>

          <Can
            allowed={
              permissions.can_ban &&
              member.status !== "banned" &&
              !member.is_owner
            }
          >
            <Button
              variant="destructive"
              onClick={() => setBanOpen(true)}
              disabled={actionMutation.isPending}
            >
              <Ban className="mr-2 h-4 w-4" />
              Ban
            </Button>
          </Can>

          <Can
            allowed={permissions.can_remove && member.status === "active"}
          >
            <Button
              variant="outline"
              onClick={() => setRemoveOpen(true)}
              disabled={actionMutation.isPending}
            >
              <UserMinus className="mr-2 h-4 w-4" />
              Remove
            </Button>
          </Can>

          <Can allowed={permissions.can_reactivate}>
            <Button
              variant="outline"
              onClick={() => setReactivateOpen(true)}
              disabled={actionMutation.isPending}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Reactivate
            </Button>
          </Can>
        </CardContent>
      </Card>

      {/* Action dialogs */}
      <ConfirmActionDialog
        open={suspendOpen}
        onOpenChange={setSuspendOpen}
        title="Suspend Member"
        description={`Suspend ${member.user.display_name || member.user.email} from ${member.account_name}?`}
        confirmLabel="Suspend"
        variant="destructive"
        showReasonField
        reasonRequired
        reasonLabel="Suspension reason"
        isLoading={actionMutation.isPending}
        onConfirm={(reason) => handleAction("suspend", reason)}
      />

      <ConfirmActionDialog
        open={banOpen}
        onOpenChange={setBanOpen}
        title="Ban Member"
        description={`Ban ${member.user.display_name || member.user.email} from ${member.account_name}? This is a severe action.`}
        confirmLabel="Ban"
        variant="destructive"
        showReasonField
        reasonRequired
        reasonLabel="Ban reason"
        isLoading={actionMutation.isPending}
        onConfirm={(reason) => handleAction("ban", reason)}
      />

      <ConfirmActionDialog
        open={removeOpen}
        onOpenChange={setRemoveOpen}
        title="Remove Member"
        description={`Remove ${member.user.display_name || member.user.email} from ${member.account_name}?`}
        confirmLabel="Remove"
        variant="destructive"
        showReasonField
        reasonRequired
        reasonLabel="Removal reason"
        isLoading={actionMutation.isPending}
        onConfirm={(reason) => handleAction("remove", reason)}
      />

      <ConfirmActionDialog
        open={reactivateOpen}
        onOpenChange={setReactivateOpen}
        title="Reactivate Member"
        description={`Reactivate ${member.user.display_name || member.user.email} in ${member.account_name}?`}
        confirmLabel="Reactivate"
        isLoading={actionMutation.isPending}
        onConfirm={() => handleAction("reactivate")}
      />
    </div>
  );
}
