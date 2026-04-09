import { getNotificationMeta } from "@/features/notifications/constants/notification-constants";
import { cn } from "@/lib/utils";

interface NotificationTypeIconProps {
  notificationType: string;
  className?: string;
}

export function NotificationTypeIcon({
  notificationType,
  className,
}: NotificationTypeIconProps) {
  const meta = getNotificationMeta(notificationType);
  const Icon = meta.icon;

  return <Icon className={cn("h-5 w-5 text-muted-foreground", className)} />;
}
