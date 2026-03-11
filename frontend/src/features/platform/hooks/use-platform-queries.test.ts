import { describe, it, expect } from "vitest";

import { platformAccountQueryOptions } from "./use-platform-queries";

describe("platformAccountQueryOptions", () => {
  it("returns correct query key and staleTime", () => {
    const opts = platformAccountQueryOptions();

    expect(opts.queryKey).toEqual(["platform", "account"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });
});
