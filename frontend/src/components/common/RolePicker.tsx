"use client";

import { useMemo } from "react";
import { Shield } from "lucide-react";

import { ComboboxField } from "@/components/common/ComboboxField";
import type { RoleListItem } from "@/types/members";

interface RolePickerProps {
  roles: RoleListItem[];
  actorRoleLevel: number;
  value: string;
  onChange: (roleId: string) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  label?: string;
}

/**
 * Role picker that filters out Owner role (level 0) and roles at or below
 * the actor's level (cannot assign roles equal to or above your own).
 */
export function RolePicker({
  roles,
  actorRoleLevel,
  value,
  onChange,
  required,
  disabled,
  error,
  label = "Role",
}: RolePickerProps) {
  const options = useMemo(() => {
    return roles
      .filter((role) => role.level > 0 && role.level > actorRoleLevel)
      .sort((a, b) => a.level - b.level)
      .map((role) => ({
        value: role.id,
        label: `${role.name} (Level ${role.level})`,
      }));
  }, [roles, actorRoleLevel]);

  return (
    <ComboboxField
      label={required ? `${label} *` : label}
      value={value}
      onChange={onChange}
      options={options}
      searchPlaceholder="Search roles..."
      emptyText="No assignable roles found"
      error={error}
      icon={Shield}
      disabled={disabled}
    />
  );
}
