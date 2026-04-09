"use client";

import { Skeleton } from "@/components/ui/skeleton";

function ConversationItemSkeleton() {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5">
      <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-center justify-between">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-3 w-10" />
        </div>
        <Skeleton className="h-3 w-40" />
      </div>
    </div>
  );
}

export function ConversationListSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: 8 }, (_, i) => (
        <ConversationItemSkeleton key={i} />
      ))}
    </div>
  );
}
