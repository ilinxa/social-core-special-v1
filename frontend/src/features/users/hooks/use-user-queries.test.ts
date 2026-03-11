import { describe, it, expect } from "vitest";

import { currentUserQueryOptions, profileQueryOptions } from "./use-user-queries";

describe("currentUserQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = currentUserQueryOptions();

    expect(opts.queryKey).toEqual(["users", "me"]);
  });

  it("uses 5-minute staleTime", () => {
    const opts = currentUserQueryOptions();

    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });

  it("disables retry", () => {
    const opts = currentUserQueryOptions();

    expect(opts.retry).toBe(false);
  });
});

describe("profileQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = profileQueryOptions();

    expect(opts.queryKey).toEqual(["users", "me", "profile"]);
  });

  it("uses 5-minute staleTime", () => {
    const opts = profileQueryOptions();

    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });
});
