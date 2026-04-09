"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { NotificationEmptyState } from "@/features/notifications/components/NotificationEmptyState";
import { NotificationItem } from "@/features/notifications/components/NotificationItem";
import { NotificationScopeTabBar } from "@/features/notifications/components/NotificationScopeTabBar";
import { NOTIFICATION_HISTORY_PAGE_SIZE } from "@/features/notifications/constants/notification-constants";
import {
  useNotificationHistory,
  useNotificationScopes,
} from "@/features/notifications/hooks/use-notification-queries";
import type { NotificationHistoryParams } from "@/features/notifications/types";

// =============================================================================
// HELPERS
// =============================================================================

function parseScopeKey(key: string): Pick<NotificationHistoryParams, "scope_type" | "scope_id"> {
  if (key === "all") return {};
  if (key === "user") return { scope_type: "user" };
  const [type, id] = key.split(":");
  return { scope_type: type as NotificationHistoryParams["scope_type"], scope_id: id };
}

// =============================================================================
// COMPONENT
// =============================================================================

export function NotificationList() {
  const [activeScope, setActiveScope] = useState("all");
  const [offset, setOffset] = useState(0);

  const { data: scopesData } = useNotificationScopes();

  const scopeFilter = parseScopeKey(activeScope);
  const params: NotificationHistoryParams = {
    limit: NOTIFICATION_HISTORY_PAGE_SIZE,
    offset,
    ...scopeFilter,
  };

  const { data, isLoading } = useNotificationHistory(params);

  const handleScopeChange = (key: string) => {
    setActiveScope(key);
    setOffset(0);
  };

  const handleLoadMore = () => {
    setOffset((prev) => prev + NOTIFICATION_HISTORY_PAGE_SIZE);
  };

  const notifications = data?.notifications ?? [];
  const hasMore = notifications.length >= NOTIFICATION_HISTORY_PAGE_SIZE;

  return (
    <div className="space-y-4">
      {/* Scope tabs */}
      {scopesData?.scopes && scopesData.scopes.length > 0 && (
        <NotificationScopeTabBar
          scopes={scopesData.scopes}
          activeScope={activeScope}
          onScopeChange={handleScopeChange}
        />
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-start gap-4 rounded-lg border p-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Notification list */}
      {!isLoading && notifications.length === 0 && (
        <NotificationEmptyState variant="empty" />
      )}

      {!isLoading && notifications.length > 0 && (
        <div className="space-y-2">
          {notifications.map((notification) => (
            <NotificationItem key={notification.id} notification={notification} />
          ))}

          {hasMore && (
            <div className="flex justify-center pt-4">
              <Button variant="outline" onClick={handleLoadMore}>
                Load more
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
