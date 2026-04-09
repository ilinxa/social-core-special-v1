"use client";

import { NotificationEmptyState } from "@/features/notifications/components/NotificationEmptyState";
import { NotificationList } from "@/features/notifications/components/NotificationList";
import { useNotificationSystemEnabled } from "@/stores/notification-store";

export function NotificationsPage() {
  const isSystemEnabled = useNotificationSystemEnabled();

  if (!isSystemEnabled) {
    return (
      <div>
        <h1 className="text-2xl font-bold">Notifications</h1>
        <div className="mt-6">
          <NotificationEmptyState variant="disabled" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Notifications</h1>
      <div className="mt-6">
        <NotificationList />
      </div>
    </div>
  );
}
