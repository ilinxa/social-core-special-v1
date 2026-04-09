"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { PreferenceCategorySection } from "@/features/notifications/components/PreferenceCategorySection";
import { useNotificationPreferences } from "@/features/notifications/hooks/use-notification-queries";
import {
  useUpdatePreference,
  useResetPreference,
} from "@/features/notifications/hooks/use-notification-mutations";

export function NotificationPreferencesPanel() {
  const { data: preferences, isLoading } = useNotificationPreferences();
  const updateMutation = useUpdatePreference();
  const resetMutation = useResetPreference();

  const handleToggle = (
    notificationType: string,
    channel: "email" | "push" | "sms",
    enabled: boolean,
  ) => {
    updateMutation.mutate({
      notificationType,
      data: { [`${channel}_enabled`]: enabled },
    });
  };

  const handleReset = (notificationType: string) => {
    resetMutation.mutate(notificationType);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (!preferences) return null;

  const categories = Object.entries(preferences);

  return (
    <div className="space-y-4">
      {categories.map(([category, items]) => (
        <PreferenceCategorySection
          key={category}
          category={category}
          items={items}
          onToggle={handleToggle}
          onReset={handleReset}
        />
      ))}
    </div>
  );
}
