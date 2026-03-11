"use client";

import { useMembershipStore } from "@/stores/membership-store";
import { NAV_CONFIG } from "@/lib/navigation-config";
import { useNavContext } from "@/hooks/use-nav-context";
import type { NavSection } from "@/types/navigation";

/**
 * Return nav sections filtered by the current context's permissions.
 *
 * - Personal context: all items (no permission gating)
 * - Business/Platform: items filtered by the user's membership permissions
 * - Empty sections are removed
 */
export function useFilteredNav(): NavSection[] {
  const context = useNavContext();
  const memberships = useMembershipStore((s) => s.memberships);

  const sections = NAV_CONFIG[context.type];

  if (context.type === "personal") {
    return sections;
  }

  const membership =
    context.type === "business"
      ? memberships.find(
          (m) =>
            m.account_type === "business" && m.account_slug === context.slug && m.status === "active",
        )
      : memberships.find((m) => m.account_type === "platform" && m.status === "active");

  if (!membership) {
    return [];
  }

  const permCodes = new Set(membership.permissions.map((p) => p.code));

  return sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => {
        if (item.ownerOnly && !membership.is_owner) return false;
        if (item.minMembers && membership.account_max_members < item.minMembers) return false;
        if (item.permission && !permCodes.has(item.permission)) return false;
        return true;
      }),
    }))
    .filter((section) => section.items.length > 0);
}
