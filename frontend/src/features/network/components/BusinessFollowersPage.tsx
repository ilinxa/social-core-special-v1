"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Search } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useHasPermission } from "@/hooks/use-has-permission";
import { useBusinessMemberships } from "@/stores/membership-store";
import {
  useBusinessFollowers,
  useBusinessNetworkStats,
} from "@/features/network/hooks/use-network-queries";
import { useRemoveBusinessFollower } from "@/features/network/hooks/use-network-mutations";
import type { FollowerItem } from "@/types/network";

function getInitials(name: string): string {
  return name[0]?.toUpperCase() ?? "?";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function FollowerCard({
  follower,
  canManage,
  onRemove,
  isRemoving,
}: {
  follower: FollowerItem;
  canManage: boolean;
  onRemove: (followId: string) => void;
  isRemoving: boolean;
}) {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="flex items-center gap-4 rounded-lg border p-4">
      <Avatar className="h-10 w-10">
        <AvatarImage
          src={follower.follower.avatar_url}
          alt={follower.follower.display_name}
        />
        <AvatarFallback>
          {getInitials(follower.follower.display_name)}
        </AvatarFallback>
      </Avatar>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{follower.follower.display_name}</p>
        <p className="text-muted-foreground text-xs">
          @{follower.follower.username}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <span className="text-muted-foreground hidden text-xs sm:block">
          {formatDate(follower.created_at)}
        </span>
        <Can allowed={canManage}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDialogOpen(true)}
            disabled={isRemoving}
          >
            Remove
          </Button>
        </Can>
      </div>

      <ConfirmActionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Remove follower?"
        description={`Remove ${follower.follower.display_name} from your followers? They can follow again later.`}
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={() => onRemove(follower.id)}
        isLoading={isRemoving}
      />
    </div>
  );
}

export function BusinessFollowersPage() {
  const { slug } = useParams<{ slug: string }>();
  const [search, setSearch] = useState("");
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";
  const canManage = useHasPermission("can_manage_followers", "business", accountId);
  const { data, isLoading } = useBusinessFollowers(slug);
  const { data: stats } = useBusinessNetworkStats(slug);
  const removeFollower = useRemoveBusinessFollower(slug);

  function handleRemove(followId: string) {
    removeFollower.mutate(followId, {
      onSuccess: () => toast.success("Follower removed"),
      onError: (error) =>
        toast.error("Failed", {
          description:
            error instanceof Error ? error.message : "Could not remove follower.",
        }),
    });
  }

  const followers = data?.results ?? [];
  const filtered = search
    ? followers.filter(
        (f) =>
          f.follower.display_name.toLowerCase().includes(search.toLowerCase()) ||
          f.follower.username.toLowerCase().includes(search.toLowerCase()),
      )
    : followers;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Followers</h1>
        {stats && (
          <span className="text-muted-foreground text-sm">
            {stats.followers_count} followers
          </span>
        )}
      </div>

      <div className="relative">
        <Search className="text-muted-foreground absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" />
        <Input
          placeholder="Search followers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

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
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((follower) => (
            <FollowerCard
              key={follower.id}
              follower={follower}
              canManage={canManage}
              onRemove={handleRemove}
              isRemoving={removeFollower.isPending}
            />
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground py-12 text-center text-sm">
          {search ? "No followers match your search." : "No followers yet."}
        </p>
      )}
    </div>
  );
}
