"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useMessageSearch } from "@/features/chat/hooks/use-chat-queries";
import type { MessageSearchResult, MessageSearchParams } from "@/features/chat/types";

interface MessageSearchPanelProps {
  scopeType?: string;
  scopeId?: string;
  onResultClick: (result: MessageSearchResult) => void;
  onClose: () => void;
}

/**
 * Search overlay panel for finding messages across conversations.
 * Debounced input (300ms), infinite scroll results.
 */
export function MessageSearchPanel({
  scopeType,
  scopeId,
  onResultClick,
  onClose,
}: MessageSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Auto-focus on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const searchParams = useMemo<MessageSearchParams>(
    () => ({
      q: debouncedQuery,
      scope_type: scopeType as MessageSearchParams["scope_type"],
      scope_id: scopeId,
    }),
    [debouncedQuery, scopeType, scopeId],
  );

  const { data, isLoading, isFetchingNextPage, hasNextPage, fetchNextPage } =
    useMessageSearch(searchParams);

  // Infinite scroll
  const { ref: bottomRef, inView } = useInView({ threshold: 0 });
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const results = useMemo(
    () => data?.pages.flatMap((page) => page.results) ?? [],
    [data],
  );

  const handleResultClick = useCallback(
    (result: MessageSearchResult) => {
      onResultClick(result);
      onClose();
    },
    [onResultClick, onClose],
  );

  return (
    <div
      className="flex h-full flex-col border-l bg-background"
      data-testid="message-search-panel"
    >
      {/* Header */}
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          placeholder="Search messages..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="h-8 border-none bg-transparent p-0 text-sm focus-visible:ring-0"
        />
        <Button variant="ghost" size="icon-sm" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Results */}
      <ScrollArea className="flex-1">
        {!debouncedQuery ? (
          <p className="p-4 text-center text-sm text-muted-foreground">
            Type to search messages
          </p>
        ) : isLoading ? (
          <SearchSkeleton />
        ) : results.length === 0 ? (
          <p className="p-4 text-center text-sm text-muted-foreground">
            No messages found for &ldquo;{debouncedQuery}&rdquo;
          </p>
        ) : (
          <div className="space-y-0.5 p-1">
            {results.map((result) => (
              <SearchResultItem
                key={result.id}
                result={result}
                onClick={handleResultClick}
              />
            ))}
            {hasNextPage && (
              <div ref={bottomRef} className="py-2">
                {isFetchingNextPage && <SearchSkeleton />}
              </div>
            )}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

function SearchResultItem({
  result,
  onClick,
}: {
  result: MessageSearchResult;
  onClick: (result: MessageSearchResult) => void;
}) {
  return (
    <button
      className="w-full rounded-md px-3 py-2 text-left hover:bg-accent"
      onClick={() => onClick(result)}
      data-testid={`search-result-${result.id}`}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-xs font-medium">
          {result.conversation_name}
        </span>
        <span className="shrink-0 text-[10px] text-muted-foreground">
          {formatSearchDate(result.created_at)}
        </span>
      </div>
      <p className="truncate text-xs text-muted-foreground">
        {result.sender_name}
      </p>
      <p className="mt-0.5 line-clamp-2 text-sm">{result.content}</p>
    </button>
  );
}

function SearchSkeleton() {
  return (
    <div className="space-y-3 p-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="space-y-1">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-4 w-full" />
        </div>
      ))}
    </div>
  );
}

function formatSearchDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  }
  if (days === 1) return "Yesterday";
  if (days < 7) {
    return date.toLocaleDateString("en-US", { weekday: "short" });
  }
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}
