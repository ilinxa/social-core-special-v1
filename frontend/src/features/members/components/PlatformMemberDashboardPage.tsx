"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Can } from "@/components/common/Can";
import { QuotaBar } from "@/components/common/QuotaBar";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { MemberList } from "./MemberList";
import { RoleList } from "./RoleList";
import { CreateRoleDialog } from "./CreateRoleDialog";
import { useMemberList } from "@/features/members/hooks/use-member-queries";
import { useRoleList } from "@/features/members/hooks/use-role-queries";
import { useCreateRole } from "@/features/members/hooks/use-role-mutations";
import { usePlatformAccount } from "@/features/platform/hooks/use-platform-queries";
import { usePlatformMembership } from "@/stores/membership-store";
import { useHasPermission } from "@/hooks/use-has-permission";
import type { MemberListParams } from "@/types/members";

export function PlatformMemberDashboardPage() {
  const router = useRouter();
  const { data: platform, isLoading: platLoading } = usePlatformAccount();
  const myMembership = usePlatformMembership();
  const actorRoleLevel = myMembership?.role.level ?? 99;
  const slug = "platform";

  const [params, setParams] = useState<MemberListParams>({});
  const { data: members, isLoading: membersLoading } = useMemberList("platform", slug, params);
  const { data: roles, isLoading: rolesLoading } = useRoleList("platform", slug);

  const accountId = myMembership?.account_id ?? "";
  const canManageRoles = useHasPermission("can_create_role", "platform", accountId);
  const [createRoleOpen, setCreateRoleOpen] = useState(false);
  const createRole = useCreateRole("platform", slug);

  function handleMemberClick(memberId: string) {
    router.push(`/pconsole/members/${memberId}`);
  }

  function handleRoleClick(roleId: string) {
    router.push(`/pconsole/members/roles/${roleId}`);
  }

  if (platLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  const memberCount = members?.count ?? 0;
  const maxMembers = platform?.max_members ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Platform Members</h1>
      </div>

      <QuotaBar current={memberCount} max={maxMembers} />

      <MemberList
        data={members}
        roles={roles}
        params={params}
        onParamsChange={setParams}
        onMemberClick={handleMemberClick}
        isLoading={membersLoading}
      />

      <Separator />

      <RoleList
        roles={roles}
        isLoading={rolesLoading}
        canCreateRole={canManageRoles}
        onCreateClick={() => setCreateRoleOpen(true)}
        onRoleClick={handleRoleClick}
      />

      <Can allowed={canManageRoles}>
        <CreateRoleDialog
          open={createRoleOpen}
          onOpenChange={setCreateRoleOpen}
          actorRoleLevel={actorRoleLevel}
          isLoading={createRole.isPending}
          onSubmit={(data) => {
            createRole.mutate(data, {
              onSuccess: () => {
                setCreateRoleOpen(false);
                toast.success("Role created successfully");
              },
              onError: () => {
                toast.error("Failed to create role");
              },
            });
          }}
        />
      </Can>
    </div>
  );
}
