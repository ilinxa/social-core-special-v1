"use client";

import { useEffect, useMemo } from "react";
import { useInView } from "react-intersection-observer";
import { Unlock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatBlocks } from "@/features/chat/hooks/use-chat-queries";
import { useUnblockParticipant } from "@/features/chat/hooks/use-chat-mutations";

/**
 * List of blocked chat participants with unblock action.
 */
export function BlockList() {
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useChatBlocks();
  const unblock = useUnblockParticipant();

  const { ref, inView } = useInView({ threshold: 0 });
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const blocks = useMemo(
    () => data?.pages.flatMap((page) => page.results) ?? [],
    [data],
  );

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (blocks.length === 0) {
    return (
      <p className="p-4 text-center text-sm text-muted-foreground">
        No blocked users
      </p>
    );
  }

  return (
    <div className="space-y-1" data-testid="block-list">
      {blocks.map((block) => (
        <div
          key={block.id}
          className="flex items-center justify-between rounded-md px-3 py-2 hover:bg-accent"
        >
          <div>
            <p className="text-sm font-medium">{block.blocked_name}</p>
            <p className="text-xs text-muted-foreground">
              Blocked {formatBlockDate(block.created_at)}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => unblock.mutate(block.id)}
            disabled={unblock.isPending}
            data-testid={`unblock-${block.id}`}
          >
            <Unlock className="mr-1.5 h-3.5 w-3.5" />
            Unblock
          </Button>
        </div>
      ))}
      {hasNextPage && (
        <div ref={ref} className="py-2">
          {isFetchingNextPage && <Skeleton className="h-12 w-full" />}
        </div>
      )}
    </div>
  );
}

function formatBlockDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
