"use client";

import { useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";

import { isGovernanceTokenValid } from "@/lib/governance-token";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface GovernanceGuardProps {
  children: React.ReactNode;
}

/**
 * Route guard for the Governance Console (/gconsole).
 *
 * Checks for a valid governance token in sessionStorage.
 * Unlike PlatformGuard (which checks RBAC membership), this checks
 * the step-up auth token issued by /api/v1/auth/governance/*.
 *
 * The /gconsole/authenticate page is exempt — it must be accessible
 * without a governance token to allow re-authentication.
 *
 * Periodically re-checks token validity and redirects when expired.
 */
export function GovernanceGuard({ children }: GovernanceGuardProps) {
  const pathname = usePathname();
  const router = useRouter();

  const isAuthPage = pathname === "/gconsole/authenticate";

  // Compute token validity synchronously (not in an effect)
  const isValid = useMemo(() => {
    if (isAuthPage) return true;
    if (typeof window === "undefined") return false;
    return isGovernanceTokenValid();
  }, [isAuthPage, pathname]);

  // Redirect if invalid (non-auth page)
  useEffect(() => {
    if (isAuthPage || isValid) return;

    const callbackUrl = encodeURIComponent(pathname);
    router.replace(`/gconsole/authenticate?callbackUrl=${callbackUrl}`);
  }, [isAuthPage, isValid, pathname, router]);

  // Periodic re-check for token expiry
  useEffect(() => {
    if (isAuthPage || !isValid) return;

    const interval = setInterval(() => {
      if (!isGovernanceTokenValid()) {
        const callbackUrl = encodeURIComponent(pathname);
        router.replace(`/gconsole/authenticate?callbackUrl=${callbackUrl}`);
      }
    }, 30_000);

    return () => clearInterval(interval);
  }, [isAuthPage, isValid, pathname, router]);

  // SSR: show skeleton until client hydrates
  if (typeof window === "undefined") {
    return (
      <div
        className="flex h-screen items-center justify-center"
        role="status"
        aria-label="Loading"
      >
        <Skeleton className="h-64 w-full max-w-2xl" />
      </div>
    );
  }

  if (!isValid && !isAuthPage) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Governance Authentication Required</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              Redirecting to step-up authentication...
            </p>
            <Link
              href="/gconsole/authenticate"
              className="text-primary hover:underline"
            >
              Authenticate now
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}
