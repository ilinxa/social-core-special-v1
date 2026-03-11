import { describe, it, expect } from "vitest";

import {
  memberListQueryOptions,
  memberDetailQueryOptions,
} from "./use-member-queries";

describe("memberListQueryOptions", () => {
  it("returns correct query key for business", () => {
    const opts = memberListQueryOptions("business", "test-biz");

    expect(opts.queryKey).toEqual(["members", "list", "business", "test-biz", undefined]);
    expect(opts.staleTime).toBe(2 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("includes params in query key", () => {
    const opts = memberListQueryOptions("business", "test-biz", {
      search: "alice",
      status: "active",
    });

    expect(opts.queryKey).toEqual([
      "members",
      "list",
      "business",
      "test-biz",
      { search: "alice", status: "active" },
    ]);
  });

  it("returns correct query key for platform", () => {
    const opts = memberListQueryOptions("platform", "platform");

    expect(opts.queryKey).toEqual(["members", "list", "platform", "platform", undefined]);
  });

  it("disables query when slug is empty", () => {
    const opts = memberListQueryOptions("business", "");

    expect(opts.enabled).toBe(false);
  });
});

describe("memberDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = memberDetailQueryOptions("business", "test-biz", "mem-1");

    expect(opts.queryKey).toEqual(["members", "detail", "mem-1"]);
    expect(opts.staleTime).toBe(2 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when slug is empty", () => {
    const opts = memberDetailQueryOptions("business", "", "mem-1");

    expect(opts.enabled).toBe(false);
  });

  it("disables query when membershipId is empty", () => {
    const opts = memberDetailQueryOptions("business", "test-biz", "");

    expect(opts.enabled).toBe(false);
  });
});
