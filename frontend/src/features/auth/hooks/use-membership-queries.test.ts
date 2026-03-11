import { describe, it, expect, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";

import { membershipsQueryOptions, invalidateMemberships } from "./use-membership-queries";

describe("membershipsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = membershipsQueryOptions();

    expect(opts.queryKey).toEqual(["users", "memberships"]);
  });

  it("uses Infinity staleTime for event-driven invalidation", () => {
    const opts = membershipsQueryOptions();

    expect(opts.staleTime).toBe(Infinity);
  });

  it("uses 30-minute gcTime", () => {
    const opts = membershipsQueryOptions();

    expect(opts.gcTime).toBe(30 * 60 * 1000);
  });

  it("always refetches on window focus", () => {
    const opts = membershipsQueryOptions();

    expect(opts.refetchOnWindowFocus).toBe("always");
  });
});

describe("invalidateMemberships", () => {
  it("calls invalidateQueries with memberships key", async () => {
    const queryClient = new QueryClient();
    const spy = vi.spyOn(queryClient, "invalidateQueries").mockResolvedValue();

    await invalidateMemberships(queryClient);

    expect(spy).toHaveBeenCalledWith({
      queryKey: ["users", "memberships"],
    });
  });
});
