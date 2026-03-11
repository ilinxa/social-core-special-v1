"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus } from "lucide-react";
import { RoleCard } from "./RoleCard";
import type { RoleListItem } from "@/types/members";

interface RoleListProps {
  roles?: RoleListItem[];
  isLoading?: boolean;
  canCreateRole?: boolean;
  onCreateClick?: () => void;
  onRoleClick?: (roleId: string) => void;
}

export function RoleList({
  roles,
  isLoading,
  canCreateRole,
  onCreateClick,
  onRoleClick,
}: RoleListProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Roles</h3>
        {canCreateRole && (
          <Button size="sm" onClick={onCreateClick}>
            <Plus className="mr-1.5 h-4 w-4" />
            Create Role
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border p-4 space-y-2">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      ) : roles?.length === 0 ? (
        <p className="py-4 text-center text-muted-foreground">No roles found.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {roles?.map((role) => (
            <RoleCard
              key={role.id}
              role={role}
              onClick={() => onRoleClick?.(role.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
