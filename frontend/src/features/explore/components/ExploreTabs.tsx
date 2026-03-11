"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type ExploreTab = "all" | "businesses" | "users";

interface ExploreTabsProps {
  activeTab: ExploreTab;
  onTabChange: (tab: ExploreTab) => void;
  showUsersTab: boolean;
}

export function ExploreTabs({ activeTab, onTabChange, showUsersTab }: ExploreTabsProps) {
  return (
    <Tabs value={activeTab} onValueChange={(v) => onTabChange(v as ExploreTab)}>
      <TabsList className="w-full">
        <TabsTrigger value="all" className="flex-1">All</TabsTrigger>
        <TabsTrigger value="businesses" className="flex-1">Businesses</TabsTrigger>
        {showUsersTab && <TabsTrigger value="users" className="flex-1">Users</TabsTrigger>}
      </TabsList>
    </Tabs>
  );
}
