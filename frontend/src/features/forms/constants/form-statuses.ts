import type { StatusConfig } from "@/components/common/StatusBadge";
import type { FormStatus, ResponseStatus } from "@/types/forms";

export const FORM_STATUS_CONFIG: Record<FormStatus, StatusConfig> = {
  draft: {
    label: "Draft",
    className: "bg-gray-100 text-gray-800",
  },
  active: {
    label: "Active",
    className: "bg-green-100 text-green-800",
  },
  archived: {
    label: "Archived",
    className: "bg-yellow-100 text-yellow-800",
  },
  deleted: {
    label: "Deleted",
    className: "bg-red-100 text-red-800",
  },
};

export const RESPONSE_STATUS_CONFIG: Record<ResponseStatus, StatusConfig> = {
  draft: {
    label: "Draft",
    className: "bg-gray-100 text-gray-800",
  },
  submitted: {
    label: "Submitted",
    className: "bg-blue-100 text-blue-800",
  },
  processed: {
    label: "Processed",
    className: "bg-green-100 text-green-800",
  },
  void: {
    label: "Void",
    className: "bg-red-100 text-red-800",
  },
  expired: {
    label: "Expired",
    className: "bg-yellow-100 text-yellow-800",
  },
};

export const FORM_STATUS_TABS = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "draft", label: "Draft" },
  { value: "archived", label: "Archived" },
] as const;

export const RESPONSE_STATUS_TABS = [
  { value: "all", label: "All" },
  { value: "submitted", label: "Submitted" },
  { value: "draft", label: "Draft" },
  { value: "processed", label: "Processed" },
  { value: "void", label: "Void" },
] as const;
