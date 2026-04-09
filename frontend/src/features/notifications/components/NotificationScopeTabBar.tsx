"use client";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { NotificationScopeItem } from "@/features/notifications/types";

// =============================================================================
// HELPERS
// =============================================================================

function scopeKey(scope: NotificationScopeItem): string {
  if (scope.scope_type === "user") return "user";
  return `${scope.scope_type}:${scope.scope_id}`;
}

function scopeLabel(scope: NotificationScopeItem): string {
  if (scope.scope_type === "user") return "Personal";
  if (scope.scope_type === "platform") return "Platform";
  return "Business";
}

// =============================================================================
// COMPONENT
// =============================================================================

interface NotificationScopeTabBarProps {
  scopes: NotificationScopeItem[];
  activeScope: string;
  onScopeChange: (scopeKey: string) => void;
}

export function NotificationScopeTabBar({
  scopes,
  activeScope,
  onScopeChange,
}: NotificationScopeTabBarProps) {
  const totalCount = scopes.reduce((sum, s) => sum + s.count, 0);

  return (
    <Tabs value={activeScope} onValueChange={onScopeChange}>
      <TabsList className="w-full justify-start overflow-x-auto">
        <TabsTrigger value="all" className="gap-1.5">
          All
          {totalCount > 0 && (
            <Badge variant="secondary" className="ml-1 h-5 min-w-5 px-1 text-[10px]">
              {totalCount}
            </Badge>
          )}
        </TabsTrigger>

        {scopes.map((scope) => {
          const key = scopeKey(scope);
          const label = scopeLabel(scope);

          return (
            <TabsTrigger key={key} value={key} className="gap-1.5">
              {label}
              {scope.count > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 min-w-5 px-1 text-[10px]"
                >
                  {scope.count}
                </Badge>
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}
