"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
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
import { useBusiness } from "@/features/business/hooks/use-business-queries";
import { useBusinessMemberships } from "@/stores/membership-store";
import { useHasPermission } from "@/hooks/use-has-permission";
import type { MemberListParams } from "@/types/members";

export function BusinessMemberDashboardPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const { data: business, isLoading: bizLoading } = useBusiness(slug);
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const actorRoleLevel = myMembership?.role.level ?? 99;

  const [params, setParams] = useState<MemberListParams>({});
  const { data: members, isLoading: membersLoading } = useMemberList("business", slug, params);
  const { data: roles, isLoading: rolesLoading } = useRoleList("business", slug);

  const accountId = myMembership?.account_id ?? "";
  const canManageRoles = useHasPermission("can_create_role", "business", accountId);
  const [createRoleOpen, setCreateRoleOpen] = useState(false);
  const createRole = useCreateRole("business", slug);

  function handleMemberClick(memberId: string) {
    router.push(`/bconsole/${slug}/members/${memberId}`);
  }

  function handleRoleClick(roleId: string) {
    router.push(`/bconsole/${slug}/members/roles/${roleId}`);
  }

  if (bizLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  const memberCount = members?.count ?? 0;
  const maxMembers = business?.max_members ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Members</h1>
      </div>

      {/* Quota bar */}
      <QuotaBar current={memberCount} max={maxMembers} />

      {/* Member list */}
      <MemberList
        data={members}
        roles={roles}
        params={params}
        onParamsChange={setParams}
        onMemberClick={handleMemberClick}
        isLoading={membersLoading}
      />

      <Separator />

      {/* Roles section */}
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
