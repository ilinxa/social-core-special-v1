"use client";

import { useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { FollowButton } from "@/features/network/components/FollowButton";
import {
  PlatformProfileSkeleton,
  PlatformProfileView,
} from "@/features/platform/components/PlatformProfileView";
import { usePlatformAccount } from "@/features/platform/hooks/use-platform-queries";

export function PlatformPublicProfilePage() {
  const queryClient = useQueryClient();
  const { data: account, isLoading, error } = usePlatformAccount();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <PlatformProfileSkeleton />
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h2 className="text-xl font-semibold">Platform profile not available</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          The platform profile could not be loaded.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <PlatformProfileView account={account} />
      <FollowButton
        followeeType="platform"
        followeeId={account.id}
        followStatus={account._relationship?.follow_status ?? null}
        followId={account._relationship?.follow_id ?? null}
        activeFollowTransaction={account._relationship?.active_follow_transaction ?? null}
        onAction={() => queryClient.invalidateQueries({ queryKey: queryKeys.platform.account() })}
      />
    </div>
  );
}
