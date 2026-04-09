import { Bell, BellOff } from "lucide-react";

interface NotificationEmptyStateProps {
  variant: "disabled" | "empty";
}

export function NotificationEmptyState({ variant }: NotificationEmptyStateProps) {
  if (variant === "disabled") {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <BellOff className="h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-medium">Notifications unavailable</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          The notification system is currently disabled for this deployment.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Bell className="h-12 w-12 text-muted-foreground/50" />
      <h3 className="mt-4 text-lg font-medium">No notifications yet</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        When you receive notifications, they will appear here.
      </p>
    </div>
  );
}
