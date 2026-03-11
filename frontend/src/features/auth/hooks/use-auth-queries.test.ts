import { describe, it, expect } from "vitest";

import { sessionsQueryOptions } from "./use-auth-queries";

describe("sessionsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = sessionsQueryOptions();

    expect(opts.queryKey).toEqual(["auth", "sessions"]);
  });
});
