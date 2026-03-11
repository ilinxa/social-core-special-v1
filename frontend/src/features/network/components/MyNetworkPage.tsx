"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { toast } from "sonner";

import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useConnections, useFollowing, useNetworkStats } from "@/features/network/hooks/use-network-queries";
import { useDisconnectUser, useUnfollow } from "@/features/network/hooks/use-network-mutations";
import { ConnectionCard } from "@/features/network/components/ConnectionCard";
import { FollowingCard } from "@/features/network/components/FollowingCard";

type TabValue = "connections" | "following";

export function MyNetworkPage() {
  const [activeTab, setActiveTab] = useState<TabValue>("connections");
  const [search, setSearch] = useState("");

  const { data: stats } = useNetworkStats();
  const { data: connectionsData, isLoading: loadingConnections } = useConnections();
  const { data: followingData, isLoading: loadingFollowing } = useFollowing();
  const disconnectUser = useDisconnectUser();
  const unfollowMutation = useUnfollow();

  function handleDisconnect(connectionId: string) {
    disconnectUser.mutate(connectionId, {
      onSuccess: () => toast.success("Disconnected"),
      onError: (error) =>
        toast.error("Failed", {
          description: error instanceof Error ? error.message : "Could not disconnect.",
        }),
    });
  }

  function handleUnfollow(followId: string) {
    unfollowMutation.mutate(followId, {
      onSuccess: () => toast.success("Unfollowed"),
      onError: (error) =>
        toast.error("Failed", {
          description: error instanceof Error ? error.message : "Could not unfollow.",
        }),
    });
  }

  const connections = connectionsData?.results ?? [];
  const following = followingData?.results ?? [];

  const filteredConnections = search
    ? connections.filter(
        (c) =>
          c.other_user.display_name.toLowerCase().includes(search.toLowerCase()) ||
          c.other_user.username.toLowerCase().includes(search.toLowerCase()),
      )
    : connections;

  const filteredFollowing = search
    ? following.filter((f) =>
        f.followee_name.toLowerCase().includes(search.toLowerCase()),
      )
    : following;

  const isLoading = activeTab === "connections" ? loadingConnections : loadingFollowing;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">My Network</h1>
        {stats && (
          <div className="text-muted-foreground flex items-center gap-3 text-sm">
            <span>{stats.connections_count} connections</span>
            <span className="text-muted-foreground/40">|</span>
            <span>{stats.following_count} following</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
        <TabsList>
          <TabsTrigger value="connections">
            Connections{connectionsData ? ` (${connectionsData.count})` : ""}
          </TabsTrigger>
          <TabsTrigger value="following">
            Following{followingData ? ` (${followingData.count})` : ""}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Search */}
      <div className="relative">
        <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
        <Input
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 rounded-lg border p-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-8 w-20" />
            </div>
          ))}
        </div>
      ) : activeTab === "connections" ? (
        filteredConnections.length > 0 ? (
          <div className="space-y-3">
            {filteredConnections.map((connection) => (
              <ConnectionCard
                key={connection.id}
                connection={connection}
                onDisconnect={handleDisconnect}
                isDisconnecting={disconnectUser.isPending}
              />
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground py-12 text-center text-sm">
            {search ? "No connections match your search." : "No connections yet."}
          </p>
        )
      ) : filteredFollowing.length > 0 ? (
        <div className="space-y-3">
          {filteredFollowing.map((item) => (
            <FollowingCard
              key={item.id}
              item={item}
              onUnfollow={handleUnfollow}
              isUnfollowing={unfollowMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground py-12 text-center text-sm">
          {search ? "No results match your search." : "Not following anyone yet."}
        </p>
      )}
    </div>
  );
}
