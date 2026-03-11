"use client";

import { useEffect, useRef } from "react";

import { useAuthStore } from "@/stores/auth-store";
import { useMembershipStore } from "@/stores/membership-store";
import { silentRefreshApi, clearSessionCookie } from "@/features/auth/api/auth-api";
import { fetchCurrentUserApi } from "@/features/users/api/users-api";
import { fetchMyMembershipsApi } from "@/features/auth/api/membership-api";
import { ApiError } from "@/lib/api-client";
import { reportError } from "@/lib/error-reporting";

export function AuthInitializer({ children }: { children: React.ReactNode }) {
  const { setUser, clearUser, setInitialized, isInitialized } = useAuthStore();
  const { setMemberships, clearMemberships } = useMembershipStore();
  const didRun = useRef(false);

  useEffect(() => {
    if (didRun.current || isInitialized) return;
    didRun.current = true;

    async function initialize() {
      try {
        await silentRefreshApi();
        const [user, memberships] = await Promise.all([
          fetchCurrentUserApi(),
          fetchMyMembershipsApi(),
        ]);
        setUser(user);
        setMemberships(memberships);
      } catch (error) {
        // 429 (rate limited): transient error — don't destroy session.
        // The user may still have a valid session; we just can't refresh right now.
        const isRateLimited = error instanceof ApiError && error.status === 429;
        if (isRateLimited) {
          // Leave session state as-is; the proactive refresh timer or
          // next page navigation will retry later.
          return;
        }

        // Silent refresh is best-effort: 400 (missing token), 401 (invalid/expired),
        // 403 (forbidden) are all expected "no session" outcomes.
        // Only report genuine server errors (5xx) or network failures.
        const isServerError = error instanceof ApiError && error.status >= 500;
        if (isServerError) {
          reportError(error, { component: "AuthInitializer", action: "initialize" });
        }
        clearUser();
        clearMemberships();
        clearSessionCookie();
      } finally {
        setInitialized();
      }
    }

    initialize();
  }, [setUser, clearUser, setInitialized, isInitialized, setMemberships, clearMemberships]);

  return <>{children}</>;
}
