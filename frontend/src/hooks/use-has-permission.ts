import { useMembershipStore } from "@/stores/membership-store";
import type { AccountType } from "@/types/rbac";

/**
 * Check if the current user has a specific permission for an account.
 *
 * This is a Tier 1 (Navigation Hints) check — used to hide/disable UI elements.
 * The backend ALWAYS enforces permissions. If the cache is stale, the backend
 * returns 403 and the error handler shows an appropriate message.
 */
export function useHasPermission(
  code: string,
  accountType: AccountType,
  accountId: string,
): boolean {
  return useMembershipStore((state) => {
    const membership = state.memberships.find(
      (m) =>
        m.account_type === accountType &&
        m.account_id === accountId &&
        m.status === "active",
    );
    if (!membership) return false;
    return membership.permissions.some((p) => p.code === code);
  });
}

/**
 * Check if the current user has an active membership for an account.
 */
export function useIsMember(accountType: AccountType, accountId: string): boolean {
  return useMembershipStore((state) =>
    state.memberships.some(
      (m) =>
        m.account_type === accountType &&
        m.account_id === accountId &&
        m.status === "active",
    ),
  );
}

/**
 * Check if the current user is the owner of an account.
 */
export function useIsOwner(accountType: AccountType, accountId: string): boolean {
  return useMembershipStore((state) =>
    state.memberships.some(
      (m) =>
        m.account_type === accountType &&
        m.account_id === accountId &&
        m.status === "active" &&
        m.is_owner,
    ),
  );
}
