import type { StatusConfig } from "@/components/common/StatusBadge";
import type { TransactionStatus, TransactionCategory } from "@/types/transactions";

export const TRANSACTION_STATUS_CONFIG: Record<TransactionStatus, StatusConfig> = {
  created: {
    label: "Created",
    className: "bg-gray-100 text-gray-800",
  },
  pending: {
    label: "Pending",
    className: "bg-blue-100 text-blue-800",
  },
  pending_review: {
    label: "Pending Review",
    className: "bg-purple-100 text-purple-800",
  },
  accepted: {
    label: "Accepted",
    className: "bg-green-100 text-green-800",
  },
  denied: {
    label: "Denied",
    className: "bg-red-100 text-red-800",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-gray-100 text-gray-800",
  },
  expired: {
    label: "Expired",
    className: "bg-yellow-100 text-yellow-800",
  },
  dismissed: {
    label: "Dismissed",
    className: "bg-gray-100 text-gray-500",
  },
  invalidated: {
    label: "Invalidated",
    className: "bg-red-100 text-red-600",
  },
  info_requested: {
    label: "Info Requested",
    className: "bg-orange-100 text-orange-800",
  },
};

export const TRANSACTION_STATUS_TABS = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "pending_review", label: "Pending Review" },
  { value: "accepted", label: "Accepted" },
  { value: "denied", label: "Denied" },
  { value: "cancelled", label: "Cancelled" },
  { value: "info_requested", label: "Info Requested" },
] as const;

export const TRANSACTION_CATEGORY_CONFIG: Record<
  TransactionCategory,
  { label: string }
> = {
  membership: { label: "Membership" },
  ownership: { label: "Ownership" },
  verification: { label: "Verification" },
  permission: { label: "Permission" },
  social: { label: "Social" },
};
