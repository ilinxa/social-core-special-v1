"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type ChatTab = "internal" | "inbox";

interface ScopeTabBarProps {
  activeTab: ChatTab;
  onTabChange: (tab: ChatTab) => void;
  showEntityInbox: boolean;
}

/**
 * Tab bar for business/platform chat pages.
 * Shows "Internal" (scoped conversations) and "Entity Inbox" (global-scope entity conversations).
 * Entity inbox tab is only visible when user has can_manage_chat permission.
 */
export function ScopeTabBar({
  activeTab,
  onTabChange,
  showEntityInbox,
}: ScopeTabBarProps) {
  if (!showEntityInbox) return null;

  return (
    <Tabs
      value={activeTab}
      onValueChange={(value) => onTabChange(value as ChatTab)}
    >
      <TabsList className="w-full">
        <TabsTrigger value="internal" className="flex-1">
          Internal
        </TabsTrigger>
        <TabsTrigger value="inbox" className="flex-1">
          Entity Inbox
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
