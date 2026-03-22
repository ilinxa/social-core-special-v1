"use client";

import { usePathname } from "next/navigation";
import { useShallow } from "zustand/react/shallow";

import { useMembershipStore } from "@/stores/membership-store";
import type { NavContext } from "@/types/navigation";

const BCONSOLE_REGEX = /^\/bconsole\/([^/]+)/;

/**
 * Derive the current navigation context from the URL pathname.
 *
 * - `/bconsole/[slug]/...` → business context (with membership lookup)
 * - `/pconsole/...` → platform context (with membership lookup)
 * - Everything else → personal context
 */
export function useNavContext(): NavContext {
  const pathname = usePathname();
  const memberships = useMembershipStore(useShallow((s) => s.memberships));

  const businessMatch = pathname.match(BCONSOLE_REGEX);
  if (businessMatch) {
    const slug = businessMatch[1];
    const membership = memberships.find(
      (m) => m.account_type === "business" && m.account_slug === slug && m.status === "active",
    );
    return {
      type: "business",
      slug,
      accountId: membership?.account_id ?? "",
      accountName: membership?.account_name ?? slug,
    };
  }

  if (pathname.startsWith("/pconsole")) {
    const membership = memberships.find(
      (m) => m.account_type === "platform" && m.status === "active",
    );
    return {
      type: "platform",
      accountId: membership?.account_id ?? "",
    };
  }

  return { type: "personal" };
}
