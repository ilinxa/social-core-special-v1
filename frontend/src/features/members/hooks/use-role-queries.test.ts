import { describe, it, expect } from "vitest";

import {
  roleListQueryOptions,
  roleDetailQueryOptions,
  allPermissionsQueryOptions,
} from "./use-role-queries";

describe("roleListQueryOptions", () => {
  it("returns correct query key for business", () => {
    const opts = roleListQueryOptions("business", "test-biz");

    expect(opts.queryKey).toEqual(["roles", "list", "business", "test-biz"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("returns correct query key for platform", () => {
    const opts = roleListQueryOptions("platform", "platform");

    expect(opts.queryKey).toEqual(["roles", "list", "platform", "platform"]);
  });

  it("disables query when slug is empty", () => {
    const opts = roleListQueryOptions("business", "");

    expect(opts.enabled).toBe(false);
  });
});

describe("roleDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = roleDetailQueryOptions("business", "test-biz", "role-1");

    expect(opts.queryKey).toEqual(["roles", "detail", "role-1"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when slug is empty", () => {
    const opts = roleDetailQueryOptions("business", "", "role-1");

    expect(opts.enabled).toBe(false);
  });

  it("disables query when roleId is empty", () => {
    const opts = roleDetailQueryOptions("business", "test-biz", "");

    expect(opts.enabled).toBe(false);
  });
});

describe("allPermissionsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = allPermissionsQueryOptions();

    expect(opts.queryKey).toEqual(["rbac", "permissions"]);
  });

  it("uses 30-minute staleTime", () => {
    const opts = allPermissionsQueryOptions();

    expect(opts.staleTime).toBe(30 * 60 * 1000);
  });
});
