"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Clock, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useGovernanceVerification } from "@/features/governance/hooks/use-governance-queries";
import type { GovernanceBusiness } from "@/types/governance";

export function GovernanceVerificationPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useGovernanceVerification({
    page,
    page_size: 20,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">
        Pending Verification Requests
      </h1>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="text-muted-foreground py-12 text-center">
          <Clock className="mx-auto mb-3 h-8 w-8" />
          <p>No pending verification requests.</p>
        </div>
      ) : (
        <>
          <p className="text-muted-foreground text-sm">
            {data.count} pending {data.count === 1 ? "request" : "requests"}
          </p>
          <div className="space-y-2">
            {data.results.map((biz: GovernanceBusiness) => (
              <Link
                key={biz.id}
                href={`/gconsole/businesses/${biz.id}`}
                className="hover:bg-muted/50 flex items-center gap-4 rounded-lg border p-4 transition-colors"
              >
                <div className="bg-muted flex h-10 w-10 items-center justify-center rounded-lg">
                  <Building2 className="text-muted-foreground h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-medium">{biz.legal_name}</p>
                    <Badge variant="outline">Pending Verification</Badge>
                  </div>
                  <p className="text-muted-foreground text-sm">
                    {biz.business_type_display} &middot; {biz.country}
                    {biz.city ? `, ${biz.city}` : ""}
                  </p>
                </div>
                <div className="text-muted-foreground hidden items-center gap-1 text-sm sm:flex">
                  <Users className="h-4 w-4" />
                  <span>{biz.member_count}</span>
                </div>
                <div className="text-muted-foreground hidden text-sm md:block">
                  {new Date(biz.created_at).toLocaleDateString()}
                </div>
              </Link>
            ))}
          </div>

          {(data.previous || data.next) && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!data.previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-muted-foreground text-sm">Page {page}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={!data.next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
