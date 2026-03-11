"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { RolePicker } from "@/components/common/RolePicker";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { MemberPermissions, RoleListItem } from "@/types/members";

interface MemberActionsProps {
  permissions: MemberPermissions;
  roles: RoleListItem[];
  actorRoleLevel: number;
  currentRoleId: string;
  memberName: string;
  onChangeRole: (roleId: string) => void;
  onSuspend: (reason?: string) => void;
  onRemove: (reason?: string) => void;
  onBan: (reason?: string) => void;
  onReactivate: () => void;
  isLoading?: boolean;
}

export function MemberActions({
  permissions,
  roles,
  actorRoleLevel,
  currentRoleId,
  memberName,
  onChangeRole,
  onSuspend,
  onRemove,
  onBan,
  onReactivate,
  isLoading,
}: MemberActionsProps) {
  const [changeRoleOpen, setChangeRoleOpen] = useState(false);
  const [suspendOpen, setSuspendOpen] = useState(false);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [banOpen, setBanOpen] = useState(false);
  const [reactivateOpen, setReactivateOpen] = useState(false);
  const [selectedRoleId, setSelectedRoleId] = useState(currentRoleId);

  return (
    <div className="flex flex-wrap gap-2">
      <Can allowed={permissions.can_change_role}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setChangeRoleOpen(true)}
        >
          Change Role
        </Button>
        <Dialog open={changeRoleOpen} onOpenChange={setChangeRoleOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Role for {memberName}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <RolePicker
                roles={roles}
                actorRoleLevel={actorRoleLevel}
                value={selectedRoleId}
                onChange={setSelectedRoleId}
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setChangeRoleOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    onChangeRole(selectedRoleId);
                    setChangeRoleOpen(false);
                  }}
                  disabled={
                    selectedRoleId === currentRoleId || !selectedRoleId || isLoading
                  }
                >
                  Save
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </Can>

      <Can allowed={permissions.can_suspend}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSuspendOpen(true)}
        >
          Suspend
        </Button>
        <ConfirmActionDialog
          open={suspendOpen}
          onOpenChange={setSuspendOpen}
          title={`Suspend ${memberName}`}
          description="This member will lose access to the account. They can be reactivated later."
          confirmLabel="Suspend"
          variant="destructive"
          showReasonField
          onConfirm={(reason) => onSuspend(reason)}
          isLoading={isLoading}
        />
      </Can>

      <Can allowed={permissions.can_remove}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setRemoveOpen(true)}
        >
          Remove
        </Button>
        <ConfirmActionDialog
          open={removeOpen}
          onOpenChange={setRemoveOpen}
          title={`Remove ${memberName}`}
          description="This member will be removed from the account."
          confirmLabel="Remove"
          variant="destructive"
          showReasonField
          onConfirm={(reason) => onRemove(reason)}
          isLoading={isLoading}
        />
      </Can>

      <Can allowed={permissions.can_ban}>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => setBanOpen(true)}
        >
          Ban
        </Button>
        <ConfirmActionDialog
          open={banOpen}
          onOpenChange={setBanOpen}
          title={`Ban ${memberName}`}
          description="This member will be permanently banned from the account."
          confirmLabel="Ban"
          variant="destructive"
          showReasonField
          reasonRequired
          onConfirm={(reason) => onBan(reason)}
          isLoading={isLoading}
        />
      </Can>

      <Can allowed={permissions.can_reactivate}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setReactivateOpen(true)}
        >
          Reactivate
        </Button>
        <ConfirmActionDialog
          open={reactivateOpen}
          onOpenChange={setReactivateOpen}
          title={`Reactivate ${memberName}`}
          description="This member will regain access to the account with their previous role."
          confirmLabel="Reactivate"
          onConfirm={() => onReactivate()}
          isLoading={isLoading}
        />
      </Can>
    </div>
  );
}
