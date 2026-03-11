"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { useIsAuthenticated } from "@/stores/auth-store";
import { useFollow, useUnfollow } from "@/features/network/hooks/use-network-mutations";
import { useCancelTransaction } from "@/features/transactions/hooks/use-transaction-mutations";
import type { ActiveTransactionSummary } from "@/types/organization";

interface FollowButtonProps {
  followeeType: "business" | "platform";
  followeeId: string;
  followStatus: string | null;
  followId: string | null;
  activeFollowTransaction: ActiveTransactionSummary | null;
  onAction?: () => void;
  size?: "default" | "sm";
}

export function FollowButton({
  followeeType,
  followeeId,
  followStatus,
  followId,
  activeFollowTransaction,
  onAction,
  size = "default",
}: FollowButtonProps) {
  const isAuthenticated = useIsAuthenticated();
  const follow = useFollow();
  const unfollow = useUnfollow();
  const cancelTransaction = useCancelTransaction();

  const [isHovered, setIsHovered] = useState(false);
  const [unfollowDialogOpen, setUnfollowDialogOpen] = useState(false);

  if (!isAuthenticated) return null;

  const isFollowing = followStatus === "active";
  const hasPendingRequest =
    !isFollowing &&
    activeFollowTransaction?.viewer_role === "initiator";

  function handleFollow() {
    follow.mutate(
      { followee_type: followeeType, followee_id: followeeId },
      {
        onSuccess: () => {
          toast.success("Followed successfully");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Follow failed", {
            description:
              error instanceof Error ? error.message : "Could not follow.",
          });
        },
      },
    );
  }

  function handleCancelRequest() {
    if (!activeFollowTransaction) return;
    cancelTransaction.mutate(
      { transactionId: activeFollowTransaction.id },
      {
        onSuccess: () => {
          toast.success("Request cancelled");
          onAction?.();
        },
        onError: (error) => {
          toast.error("Cancel failed", {
            description:
              error instanceof Error ? error.message : "Could not cancel.",
          });
        },
      },
    );
  }

  function handleUnfollow() {
    if (!followId) return;
    unfollow.mutate(followId, {
      onSuccess: () => {
        setUnfollowDialogOpen(false);
        toast.success("Unfollowed");
        onAction?.();
      },
      onError: (error) => {
        toast.error("Unfollow failed", {
          description:
            error instanceof Error ? error.message : "Could not unfollow.",
        });
      },
    });
  }

  // State: Pending follow request — show Cancel
  if (hasPendingRequest) {
    return (
      <Button
        variant="outline"
        size={size}
        onClick={handleCancelRequest}
        disabled={cancelTransaction.isPending}
      >
        {cancelTransaction.isPending ? "Cancelling..." : "Cancel Request"}
      </Button>
    );
  }

  // State: Already following — hover to show Unfollow
  if (isFollowing) {
    return (
      <>
        <Button
          variant={isHovered ? "destructive" : "secondary"}
          size={size}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onClick={() => setUnfollowDialogOpen(true)}
        >
          {isHovered ? "Unfollow" : "Following"}
        </Button>

        <ConfirmActionDialog
          open={unfollowDialogOpen}
          onOpenChange={setUnfollowDialogOpen}
          title="Unfollow?"
          description="You will stop seeing updates from this account."
          confirmLabel="Unfollow"
          variant="destructive"
          onConfirm={handleUnfollow}
          isLoading={unfollow.isPending}
        />
      </>
    );
  }

  // State: Not following — show Follow button
  return (
    <Button
      variant="outline"
      size={size}
      onClick={handleFollow}
      disabled={follow.isPending}
    >
      {follow.isPending ? "Following..." : "Follow"}
    </Button>
  );
}
