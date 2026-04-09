"use client";

import { Separator } from "@/components/ui/separator";
import { DangerZone } from "@/features/settings/components/DangerZone";
import { NotificationPreferencesPanel } from "@/features/notifications/components/NotificationPreferencesPanel";
import { UsernameSection } from "@/features/settings/components/UsernameSection";
import { useNotificationSystemEnabled } from "@/stores/notification-store";
import { useUser } from "@/stores/auth-store";

export default function SettingsPage() {
  const user = useUser();
  const notificationsEnabled = useNotificationSystemEnabled();

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Settings</h1>

      <UsernameSection currentUsername={user.username} />

      <Separator />

      {notificationsEnabled && (
        <>
          <div>
            <h2 className="text-lg font-semibold">Notification Preferences</h2>
            <p className="text-sm text-muted-foreground">
              Choose how you want to be notified for each type of activity.
            </p>
          </div>
          <NotificationPreferencesPanel />
          <Separator />
        </>
      )}

      <DangerZone />
    </div>
  );
}
