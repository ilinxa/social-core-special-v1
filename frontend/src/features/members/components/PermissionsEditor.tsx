"use client";

import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search } from "lucide-react";
import type { Permission, RolePermission } from "@/types/members";

interface PermissionsEditorProps {
  allPermissions: Permission[];
  rolePermissions: RolePermission[];
  canModify: boolean;
  onAdd: (permissionId: string, scope: string) => void;
  onRemove: (permissionId: string) => void;
}

export function PermissionsEditor({
  allPermissions,
  rolePermissions,
  canModify,
  onAdd,
  onRemove,
}: PermissionsEditorProps) {
  const [search, setSearch] = useState("");

  const assignedIds = useMemo(
    () => new Set(rolePermissions.map((rp) => rp.permission.id)),
    [rolePermissions],
  );

  const assignedScopeMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const rp of rolePermissions) {
      map.set(rp.permission.id, rp.scope);
    }
    return map;
  }, [rolePermissions]);

  const categories = useMemo(() => {
    const catMap = new Map<string, Permission[]>();
    for (const perm of allPermissions) {
      const cat = perm.category || "General";
      if (!catMap.has(cat)) catMap.set(cat, []);
      catMap.get(cat)!.push(perm);
    }
    return Array.from(catMap.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [allPermissions]);

  const filteredCategories = useMemo(() => {
    if (!search.trim()) return categories;
    const q = search.toLowerCase();
    return categories
      .map(([cat, perms]) => [
        cat,
        perms.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            p.code.toLowerCase().includes(q) ||
            p.description.toLowerCase().includes(q),
        ),
      ] as [string, Permission[]])
      .filter(([, perms]) => perms.length > 0);
  }, [categories, search]);

  function handleToggle(permission: Permission) {
    if (assignedIds.has(permission.id)) {
      onRemove(permission.id);
    } else {
      const defaultScope = permission.applicable_scopes[0] ?? "business";
      onAdd(permission.id, defaultScope);
    }
  }

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search permissions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <div className="space-y-6">
        {filteredCategories.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No permissions match your search.
          </p>
        ) : (
          filteredCategories.map(([category, permissions]) => (
            <div key={category}>
              <h4 className="text-sm font-medium text-muted-foreground mb-3 capitalize">
                {category.replace(/_/g, " ")}
              </h4>
              <div className="space-y-2">
                {permissions.map((perm) => {
                  const isAssigned = assignedIds.has(perm.id);
                  const currentScope = assignedScopeMap.get(perm.id);

                  return (
                    <div
                      key={perm.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <Switch
                          id={`perm-${perm.id}`}
                          checked={isAssigned}
                          onCheckedChange={() => handleToggle(perm)}
                          disabled={!canModify}
                        />
                        <Label
                          htmlFor={`perm-${perm.id}`}
                          className="cursor-pointer min-w-0"
                        >
                          <span className="block font-medium text-sm">
                            {perm.name}
                          </span>
                          <span className="block text-xs text-muted-foreground truncate">
                            {perm.description}
                          </span>
                        </Label>
                      </div>

                      {isAssigned &&
                        perm.applicable_scopes.length > 1 &&
                        canModify && (
                          <Select
                            value={currentScope}
                            onValueChange={(scope) => {
                              onRemove(perm.id);
                              onAdd(perm.id, scope);
                            }}
                          >
                            <SelectTrigger className="w-[120px] ml-2">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {perm.applicable_scopes.map((scope) => (
                                <SelectItem key={scope} value={scope}>
                                  {scope}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
