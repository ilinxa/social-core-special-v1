import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";

import type { AccountType, Membership } from "@/types/rbac";

interface MembershipState {
  memberships: Membership[];
  isLoaded: boolean;
}

interface MembershipActions {
  setMemberships: (memberships: Membership[]) => void;
  clearMemberships: () => void;
}

export const useMembershipStore = create<MembershipState & MembershipActions>()(
  devtools(
    (set) => ({
      memberships: [],
      isLoaded: false,

      setMemberships: (memberships) => set({ memberships, isLoaded: true }, false, "setMemberships"),
      clearMemberships: () => set({ memberships: [], isLoaded: false }, false, "clearMemberships"),
    }),
    { name: "membership-store" },
  ),
);

// Derived selectors
function getBusinessMemberships(state: MembershipState): Membership[] {
  return state.memberships.filter(
    (m) => m.account_type === "business" && m.status === "active",
  );
}

function getPlatformMembership(state: MembershipState): Membership | null {
  return (
    state.memberships.find(
      (m) => m.account_type === "platform" && m.status === "active",
    ) ?? null
  );
}

function getMembershipForAccount(
  state: MembershipState,
  accountType: AccountType,
  accountId: string,
): Membership | null {
  return (
    state.memberships.find(
      (m) => m.account_type === accountType && m.account_id === accountId && m.status === "active",
    ) ?? null
  );
}

// Selector hooks
export function useMemberships() {
  return useMembershipStore((s) => s.memberships);
}

export function useBusinessMemberships() {
  return useMembershipStore(useShallow(getBusinessMemberships));
}

export function usePlatformMembership() {
  return useMembershipStore(getPlatformMembership);
}

export function useMembershipsLoaded() {
  return useMembershipStore((s) => s.isLoaded);
}

// Non-React access
export function getMembershipStore() {
  return useMembershipStore.getState();
}

// Exported for guards and permission hooks
export { getMembershipForAccount };
