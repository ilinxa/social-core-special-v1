"use client";

import { useEffect } from "react";
import { useInView } from "react-intersection-observer";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInfiniteBusinessSearch } from "@/features/explore/hooks/use-explore-queries";
import type { BusinessSearchParams } from "@/types/explore";
import { BusinessCard } from "./BusinessCard";

interface BusinessSearchContentProps {
  params: Omit<BusinessSearchParams, "page">;
}

function BusinessCardSkeleton() {
  return (
    <Card>
      <CardContent className="flex gap-4 p-4">
        <Skeleton className="h-12 w-12 shrink-0 rounded-lg" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
          <Skeleton className="h-3 w-24" />
        </div>
      </CardContent>
    </Card>
  );
}

export function BusinessSearchContent({ params }: BusinessSearchContentProps) {
  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteBusinessSearch(params);

  const { ref, inView } = useInView({ threshold: 0 });

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <BusinessCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  const allResults = data?.pages.flatMap((page) => page.results) ?? [];
  const totalCount = data?.pages[0]?.count ?? 0;

  return (
    <div>
      {/* Result count */}
      <p className="mb-4 text-sm text-muted-foreground">
        {totalCount} {totalCount === 1 ? "business" : "businesses"} found
      </p>

      {/* Results */}
      {allResults.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {allResults.map((biz) => (
            <BusinessCard key={biz.id} business={biz} />
          ))}
        </div>
      ) : (
        <p className="py-12 text-center text-sm text-muted-foreground">
          No businesses match your search
        </p>
      )}

      {/* Infinite scroll trigger */}
      {hasNextPage && (
        <div ref={ref} className="py-6">
          {isFetchingNextPage && (
            <div className="grid gap-3 sm:grid-cols-2">
              {[0, 1].map((i) => (
                <BusinessCardSkeleton key={i} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
