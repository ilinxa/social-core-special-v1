"use client";

import Link from "next/link";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { NotificationEmptyState } from "@/features/notifications/components/NotificationEmptyState";
import { NotificationItem } from "@/features/notifications/components/NotificationItem";
import { NOTIFICATION_DROPDOWN_LIMIT } from "@/features/notifications/constants/notification-constants";
import { useNotificationHistory } from "@/features/notifications/hooks/use-notification-queries";
import { useNotificationStore } from "@/stores/notification-store";

export function NotificationDropdown() {
  const setDropdownOpen = useNotificationStore((s) => s.setDropdownOpen);
  const { data, isLoading } = useNotificationHistory({
    limit: NOTIFICATION_DROPDOWN_LIMIT,
  });

  const notifications = data?.notifications ?? [];

  return (
    <div className="w-80">
      <div className="px-4 py-3">
        <h4 className="text-sm font-semibold">Notifications</h4>
      </div>

      <Separator />

      <ScrollArea className="max-h-80">
        {isLoading && (
          <div className="space-y-1 p-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 px-3 py-2.5">
                <Skeleton className="h-4 w-4 rounded" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3.5 w-36" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && notifications.length === 0 && (
          <div className="py-8">
            <NotificationEmptyState variant="empty" />
          </div>
        )}

        {!isLoading && notifications.length > 0 && (
          <div>
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                compact
              />
            ))}
          </div>
        )}
      </ScrollArea>

      <Separator />

      <div className="p-2">
        <Link
          href="/notifications"
          className="block rounded-md px-3 py-2 text-center text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          onClick={() => setDropdownOpen(false)}
        >
          View all notifications
        </Link>
      </div>
    </div>
  );
}
