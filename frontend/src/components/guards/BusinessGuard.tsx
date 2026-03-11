"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { useMembershipStore, useMembershipsLoaded } from "@/stores/membership-store";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface BusinessGuardProps {
  children: React.ReactNode;
}

export function BusinessGuard({ children }: BusinessGuardProps) {
  const { slug } = useParams<{ slug: string }>();
  const isLoaded = useMembershipsLoaded();
  const [hasRevalidated, setHasRevalidated] = useState(false);
  const [isRevalidating, setIsRevalidating] = useState(false);
  const revalidatingRef = useRef(false);

  const membership = useMembershipStore((s) =>
    s.memberships.find(
      (m) =>
        m.account_type === "business" &&
        m.account_slug === slug &&
        (m.status === "active" || m.status === "pending_approval"),
    ) ?? null,
  );

  useEffect(() => {
    if (isLoaded && !membership && !revalidatingRef.current && !hasRevalidated) {
      revalidatingRef.current = true;
      setIsRevalidating(true);
      fetchMyMembershipsApi()
        .then((memberships) => {
          useMembershipStore.getState().setMemberships(memberships);
        })
        .catch(() => {
          // Failed to refetch — proceed with current cache
        })
        .finally(() => {
          setHasRevalidated(true);
          setIsRevalidating(false);
        });
    }
  }, [isLoaded, membership, hasRevalidated]);

  if (!isLoaded || isRevalidating) {
    return (
      <div className="flex h-screen items-center justify-center" role="status" aria-label="Loading">
        <Skeleton className="h-64 w-full max-w-2xl" />
      </div>
    );
  }

  if (!membership) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Access Denied</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              You do not have an active membership for this business.
            </p>
            <Link href="/home" className="text-primary hover:underline">
              Back to Home
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (membership.status === "pending_approval") {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Pending Review</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Your membership is pending document review. You will get full
              access once the business approves your submission.
            </p>
            <Link href="/home" className="text-primary hover:underline">
              Back to Home
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}
