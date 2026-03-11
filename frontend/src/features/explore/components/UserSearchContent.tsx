"use client";

import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useInView } from "react-intersection-observer";

import { useInfiniteUserSearch } from "@/features/explore/hooks/use-explore-queries";
import type { UserSearchParams } from "@/types/explore";
import { UserCard } from "./UserCard";

interface UserSearchContentProps {
  params: Omit<UserSearchParams, "page">;
}

export function UserSearchContent({ params }: UserSearchContentProps) {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteUserSearch(params);

  const { ref, inView } = useInView({ threshold: 0 });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const allResults = data?.pages.flatMap((page) => page.results) ?? [];
  const totalCount = data?.pages[0]?.count ?? 0;

  return (
    <div>
      {/* Result count */}
      <p className="mb-4 text-sm text-muted-foreground">
        {totalCount} {totalCount === 1 ? "user" : "users"} found
      </p>

      {/* Results */}
      {allResults.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {allResults.map((u) => (
            <UserCard key={u.id} user={u} />
          ))}
        </div>
      ) : (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No users match your search
        </p>
      )}

      {/* Infinite scroll trigger */}
      {hasNextPage && (
        <div ref={ref} className="flex items-center justify-center py-6">
          {isFetchingNextPage && (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          )}
        </div>
      )}
    </div>
  );
}
