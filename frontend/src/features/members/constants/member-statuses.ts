import type { StatusConfig } from "@/components/common/StatusBadge";
import type { MembershipStatus } from "@/types/rbac";

export const MEMBER_STATUS_CONFIG: Record<MembershipStatus, StatusConfig> = {
  active: {
    label: "Active",
    className: "bg-green-100 text-green-800",
  },
  pending_approval: {
    label: "Pending Approval",
    className: "bg-purple-100 text-purple-800",
  },
  suspended: {
    label: "Suspended",
    className: "bg-yellow-100 text-yellow-800",
  },
  left: {
    label: "Left",
    className: "bg-gray-100 text-gray-600",
  },
  removed: {
    label: "Removed",
    className: "bg-gray-100 text-gray-800",
  },
  banned: {
    label: "Banned",
    className: "bg-red-100 text-red-800",
  },
};

export const MEMBER_STATUS_TABS = [
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
  { value: "removed", label: "Removed" },
  { value: "banned", label: "Banned" },
] as const;

export const MEMBER_ORDERING_OPTIONS = [
  { value: "name", label: "Name (A-Z)" },
  { value: "-name", label: "Name (Z-A)" },
  { value: "newest", label: "Newest first" },
  { value: "-newest", label: "Oldest first" },
] as const;
