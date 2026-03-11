import type { StatusConfig } from "@/components/common/StatusBadge";

export const CONNECTION_STATUS_CONFIG: Record<string, StatusConfig> = {
  active: {
    label: "Connected",
    className: "bg-green-100 text-green-800",
  },
  disconnected: {
    label: "Disconnected",
    className: "bg-gray-100 text-gray-600",
  },
};

export const FOLLOW_STATUS_CONFIG: Record<string, StatusConfig> = {
  active: {
    label: "Following",
    className: "bg-blue-100 text-blue-800",
  },
  removed: {
    label: "Removed",
    className: "bg-gray-100 text-gray-600",
  },
};
