"use client";

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft } from "lucide-react";
import { MemberProfile } from "./MemberProfile";
import { MemberActions } from "./MemberActions";
import { useMemberDetail } from "@/features/members/hooks/use-member-queries";
import { useRoleList } from "@/features/members/hooks/use-role-queries";
import {
  useChangeMemberRole,
  useSuspendMember,
  useRemoveMember,
  useBanMember,
  useReactivateMember,
} from "@/features/members/hooks/use-member-mutations";
import { useBusinessMemberships } from "@/stores/membership-store";
import type { AccountType } from "@/types/rbac";

interface MemberDetailPageInnerProps {
  accountType: AccountType;
  slug: string;
  backUrl: string;
}

export function MemberDetailPageInner({
  accountType,
  slug,
  backUrl,
}: MemberDetailPageInnerProps) {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: member, isLoading } = useMemberDetail(accountType, slug, id);
  const { data: roles } = useRoleList(accountType, slug);
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const actorRoleLevel = myMembership?.role.level ?? 99;

  const changeRole = useChangeMemberRole(accountType, slug);
  const suspend = useSuspendMember(accountType, slug);
  const remove = useRemoveMember(accountType, slug);
  const ban = useBanMember(accountType, slug);
  const reactivate = useReactivateMember(accountType, slug);

  if (isLoading || !member) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const memberName = member.user.display_name || member.user.username;
  const isActionLoading =
    changeRole.isPending ||
    suspend.isPending ||
    remove.isPending ||
    ban.isPending ||
    reactivate.isPending;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push(backUrl)}>
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        Back to Members
      </Button>

      <MemberProfile member={member} />

      <MemberActions
        permissions={member._permissions}
        roles={roles ?? []}
        actorRoleLevel={actorRoleLevel}
        currentRoleId={member.role.id}
        memberName={memberName}
        isLoading={isActionLoading}
        onChangeRole={(roleId) => {
          changeRole.mutate(
            { membershipId: id, data: { role_id: roleId } },
            {
              onSuccess: () => toast.success("Role changed"),
              onError: () => toast.error("Failed to change role"),
            },
          );
        }}
        onSuspend={(reason) => {
          suspend.mutate(
            { membershipId: id, data: reason ? { reason } : undefined },
            {
              onSuccess: () => toast.success("Member suspended"),
              onError: () => toast.error("Failed to suspend member"),
            },
          );
        }}
        onRemove={(reason) => {
          remove.mutate(
            { membershipId: id, data: reason ? { reason } : undefined },
            {
              onSuccess: () => {
                toast.success("Member removed");
                router.push(backUrl);
              },
              onError: () => toast.error("Failed to remove member"),
            },
          );
        }}
        onBan={(reason) => {
          ban.mutate(
            { membershipId: id, data: reason ? { reason } : undefined },
            {
              onSuccess: () => {
                toast.success("Member banned");
                router.push(backUrl);
              },
              onError: () => toast.error("Failed to ban member"),
            },
          );
        }}
        onReactivate={() => {
          reactivate.mutate(
            { membershipId: id },
            {
              onSuccess: () => toast.success("Member reactivated"),
              onError: () => toast.error("Failed to reactivate member"),
            },
          );
        }}
      />
    </div>
  );
}

export function BusinessMemberDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  return (
    <MemberDetailPageInner
      accountType="business"
      slug={slug}
      backUrl={`/bconsole/${slug}/members`}
    />
  );
}
