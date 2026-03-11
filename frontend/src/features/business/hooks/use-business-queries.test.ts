import { describe, it, expect } from "vitest";

import {
  myBusinessesQueryOptions,
  businessDetailQueryOptions,
} from "./use-business-queries";

describe("myBusinessesQueryOptions", () => {
  it("returns correct query key and staleTime", () => {
    const opts = myBusinessesQueryOptions();

    expect(opts.queryKey).toEqual(["business", "my"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });
});

describe("businessDetailQueryOptions", () => {
  it("returns correct query key including slug", () => {
    const opts = businessDetailQueryOptions("my-business");

    expect(opts.queryKey).toEqual(["business", "detail", "my-business"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when slug is empty", () => {
    const opts = businessDetailQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});
