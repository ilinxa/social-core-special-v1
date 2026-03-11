"use client";

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { PermissionsEditor } from "./PermissionsEditor";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useRoleDetail, useAllPermissions } from "@/features/members/hooks/use-role-queries";
import {
  useUpdateRole,
  useDeleteRole,
  useAddPermission,
  useRemovePermission,
} from "@/features/members/hooks/use-role-mutations";
import type { AccountType } from "@/types/rbac";

interface RoleDetailPageInnerProps {
  accountType: AccountType;
  slug: string;
  backUrl: string;
}

export function RoleDetailPageInner({
  accountType,
  slug,
  backUrl,
}: RoleDetailPageInnerProps) {
  const params = useParams<{ id: string }>();
  const roleId = params.id;
  const router = useRouter();

  const { data: role, isLoading } = useRoleDetail(accountType, slug, roleId);
  const { data: allPermissions } = useAllPermissions();
  const updateRole = useUpdateRole(accountType, slug, roleId);
  const deleteRole = useDeleteRole(accountType, slug);
  const addPermission = useAddPermission(accountType, slug, roleId);
  const removePermission = useRemovePermission(accountType, slug, roleId);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editName, setEditName] = useState<string | null>(null);
  const [editDesc, setEditDesc] = useState<string | null>(null);

  if (isLoading || !role) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const isEditing = editName !== null;

  function startEditing() {
    setEditName(role!.name);
    setEditDesc(role!.description);
  }

  function cancelEditing() {
    setEditName(null);
    setEditDesc(null);
  }

  function saveEditing() {
    if (editName === null) return;
    updateRole.mutate(
      { name: editName, description: editDesc ?? undefined },
      {
        onSuccess: () => {
          cancelEditing();
          toast.success("Role updated");
        },
        onError: () => toast.error("Failed to update role"),
      },
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Button variant="ghost" size="sm" onClick={() => router.push(backUrl)}>
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        Back to Members
      </Button>

      {/* Role header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Role Details</CardTitle>
            <div className="flex items-center gap-2">
              {role.is_system_role && (
                <Badge variant="secondary">System</Badge>
              )}
              <Badge variant="outline">Level {role.level}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="edit-role-name">Name</Label>
                <Input
                  id="edit-role-name"
                  value={editName ?? ""}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-role-desc">Description</Label>
                <Textarea
                  id="edit-role-desc"
                  value={editDesc ?? ""}
                  onChange={(e) => setEditDesc(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={saveEditing}
                  disabled={updateRole.isPending}
                >
                  {updateRole.isPending ? "Saving..." : "Save"}
                </Button>
                <Button size="sm" variant="outline" onClick={cancelEditing}>
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <>
              <div>
                <span className="text-sm text-muted-foreground">Name</span>
                <p className="font-medium">{role.name}</p>
              </div>
              {role.description && (
                <div>
                  <span className="text-sm text-muted-foreground">Description</span>
                  <p>{role.description}</p>
                </div>
              )}
              <Can allowed={role._permissions.can_edit}>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={startEditing}>
                    Edit
                  </Button>
                  <Can allowed={role._permissions.can_delete}>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => setDeleteOpen(true)}
                    >
                      Delete
                    </Button>
                  </Can>
                </div>
              </Can>
            </>
          )}
        </CardContent>
      </Card>

      <Separator />

      {/* Permissions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">
          Permissions ({role.permission_count})
        </h3>
        <PermissionsEditor
          allPermissions={allPermissions ?? []}
          rolePermissions={role.role_permissions}
          canModify={role._permissions.can_modify_permissions}
          onAdd={(permissionId, scope) => {
            addPermission.mutate(
              { permission_id: permissionId, scope },
              {
                onSuccess: () => toast.success("Permission added"),
                onError: () => toast.error("Failed to add permission"),
              },
            );
          }}
          onRemove={(permissionId) => {
            removePermission.mutate(
              { permission_id: permissionId },
              {
                onSuccess: () => toast.success("Permission removed"),
                onError: () => toast.error("Failed to remove permission"),
              },
            );
          }}
        />
      </div>

      {/* Delete dialog */}
      <ConfirmActionDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={`Delete ${role.name}`}
        description="This will permanently delete this role. Members with this role will need to be reassigned."
        confirmLabel="Delete"
        variant="destructive"
        isLoading={deleteRole.isPending}
        onConfirm={() => {
          deleteRole.mutate(roleId, {
            onSuccess: () => {
              toast.success("Role deleted");
              router.push(backUrl);
            },
            onError: () => toast.error("Failed to delete role"),
          });
        }}
      />
    </div>
  );
}

export function BusinessRoleDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  return (
    <RoleDetailPageInner
      accountType="business"
      slug={slug}
      backUrl={`/bconsole/${slug}/members`}
    />
  );
}
