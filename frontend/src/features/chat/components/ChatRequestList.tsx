"use client";

import { useEffect, useMemo } from "react";
import { useInView } from "react-intersection-observer";
import { MessageSquare } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatRequests } from "@/features/chat/hooks/use-chat-queries";
import { ChatRequestCard } from "./ChatRequestCard";

/**
 * Pending chat requests section.
 * Shown in the global-scope conversation list sidebar.
 */
export function ChatRequestList() {
  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useChatRequests();

  const { ref, inView } = useInView({ threshold: 0 });
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const requests = useMemo(
    () => data?.pages.flatMap((page) => page.results) ?? [],
    [data],
  );

  if (isLoading) {
    return (
      <div className="space-y-2 p-3">
        {[0, 1].map((i) => (
          <Skeleton key={i} className="h-24 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (requests.length === 0) {
    return null;
  }

  return (
    <div data-testid="chat-request-list">
      <div className="flex items-center gap-2 px-3 py-2">
        <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
        <h3 className="text-xs font-semibold uppercase text-muted-foreground">
          Message Requests ({requests.length})
        </h3>
      </div>
      <ScrollArea className="max-h-60">
        <div className="space-y-2 px-3 pb-2">
          {requests.map((request) => (
            <ChatRequestCard key={request.conversation_id} request={request} />
          ))}
          {hasNextPage && (
            <div ref={ref} className="py-1">
              {isFetchingNextPage && <Skeleton className="h-24 w-full rounded-lg" />}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
