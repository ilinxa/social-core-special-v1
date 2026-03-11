"use client";

import { useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import type { FollowingItem } from "@/types/network";

interface FollowingCardProps {
  item: FollowingItem;
  onUnfollow: (followId: string) => void;
  isUnfollowing?: boolean;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function FollowingCard({
  item,
  onUnfollow,
  isUnfollowing = false,
}: FollowingCardProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  const href =
    item.followee_type === "business" && item.followee_slug
      ? `/business/${item.followee_slug}`
      : item.followee_type === "platform"
        ? "/platform/profile"
        : "#";

  return (
    <div className="flex items-center gap-4 rounded-lg border p-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link href={href} className="text-sm font-medium hover:underline">
            {item.followee_name}
          </Link>
          <Badge variant="secondary" className="text-xs capitalize">
            {item.followee_type}
          </Badge>
        </div>
        <p className="text-muted-foreground mt-0.5 text-xs">
          Following since {formatDate(item.created_at)}
        </p>
      </div>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => setDialogOpen(true)}
        disabled={isUnfollowing}
      >
        Unfollow
      </Button>

      <ConfirmActionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        title="Unfollow?"
        description={`You will stop seeing updates from ${item.followee_name}.`}
        confirmLabel="Unfollow"
        variant="destructive"
        onConfirm={() => onUnfollow(item.id)}
        isLoading={isUnfollowing}
      />
    </div>
  );
}
