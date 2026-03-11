"use client";

import { Monitor, Smartphone, HelpCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessions } from "@/features/auth/hooks/use-auth-queries";
import { useLogoutAll, useRevokeSession } from "@/features/auth/hooks/use-auth-mutations";
import type { DeviceSession } from "@/features/auth/types";

function DeviceIcon({ type }: { type: DeviceSession["device_type"] }) {
  switch (type) {
    case "web":
    case "desktop":
      return <Monitor className="size-5" />;
    case "ios":
    case "android":
      return <Smartphone className="size-5" />;
    default:
      return <HelpCircle className="size-5" />;
  }
}

function formatLastActivity(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

function SessionItem({ session }: { session: DeviceSession }) {
  const revokeSession = useRevokeSession();

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className="text-muted-foreground">
          <DeviceIcon type={session.device_type} />
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{session.device_name || "Unknown device"}</p>
            {session.is_current && (
              <span className="bg-primary/10 text-primary rounded-full px-2 py-0.5 text-xs font-medium">
                Current
              </span>
            )}
          </div>
          <p className="text-muted-foreground text-xs">
            {[session.ip_address, session.location].filter(Boolean).join(" · ")} ·{" "}
            {formatLastActivity(session.last_activity)}
          </p>
        </div>
        {!session.is_current && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => revokeSession.mutate(session.id)}
            disabled={revokeSession.isPending}
          >
            Revoke
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function SessionList() {
  const { data: sessions, isLoading, error } = useSessions();
  const logoutAll = useLogoutAll();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-destructive text-sm">Failed to load sessions. Please try again.</p>;
  }

  if (!sessions || sessions.length === 0) {
    return <p className="text-muted-foreground text-sm">No active sessions found.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {sessions.map((session) => (
          <SessionItem key={session.id} session={session} />
        ))}
      </div>

      {sessions.length > 1 && (
        <Button
          variant="destructive"
          className="w-full"
          onClick={() => logoutAll.mutate()}
          disabled={logoutAll.isPending}
        >
          {logoutAll.isPending ? "Signing out..." : "Sign Out Everywhere"}
        </Button>
      )}
    </div>
  );
}
