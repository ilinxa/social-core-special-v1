import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface StatusConfig {
  label: string;
  className: string;
}

interface StatusBadgeProps<T extends string> {
  status: T;
  statusMap: Record<T, StatusConfig>;
  className?: string;
}

/**
 * Generic status badge with configurable label and color per status.
 *
 * @example
 * const memberStatusMap = {
 *   active: { label: "Active", className: "bg-green-100 text-green-800" },
 *   suspended: { label: "Suspended", className: "bg-yellow-100 text-yellow-800" },
 * };
 * <StatusBadge status={member.status} statusMap={memberStatusMap} />
 */
export function StatusBadge<T extends string>({
  status,
  statusMap,
  className,
}: StatusBadgeProps<T>) {
  const config = statusMap[status];

  if (!config) {
    return (
      <Badge variant="outline" className={className}>
        {status}
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className={cn(config.className, "border-transparent", className)}
    >
      {config.label}
    </Badge>
  );
}
