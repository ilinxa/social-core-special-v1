import { describe, it, expect } from "vitest";

import {
  exploreCombinedQueryOptions,
  tagSuggestionsQueryOptions,
  citiesQueryOptions,
} from "./use-explore-queries";

// =============================================================================
// exploreCombinedQueryOptions
// =============================================================================

describe("exploreCombinedQueryOptions", () => {
  it("returns correct query key with params and auth flag", () => {
    const opts = exploreCombinedQueryOptions({ q: "test" }, true);

    expect(opts.queryKey).toEqual(["explore", "combined", { q: "test" }, true]);
  });

  it("includes isAuthenticated=false in key", () => {
    const opts = exploreCombinedQueryOptions({ q: "test" }, false);

    expect(opts.queryKey).toEqual(["explore", "combined", { q: "test" }, false]);
  });

  it("uses 30-second staleTime", () => {
    const opts = exploreCombinedQueryOptions({}, true);

    expect(opts.staleTime).toBe(30 * 1000);
  });
});

// =============================================================================
// tagSuggestionsQueryOptions
// =============================================================================

describe("tagSuggestionsQueryOptions", () => {
  it("returns correct query key with q and category", () => {
    const opts = tagSuggestionsQueryOptions("react", "user");

    expect(opts.queryKey).toEqual(["explore", "tags", "react", "user"]);
  });

  it("uses 5-minute staleTime", () => {
    const opts = tagSuggestionsQueryOptions("react");

    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });

  it("enables query when q has at least 1 character", () => {
    const opts = tagSuggestionsQueryOptions("r");

    expect(opts.enabled).toBe(true);
  });

  it("disables query when q is empty", () => {
    const opts = tagSuggestionsQueryOptions("");

    expect(opts.enabled).toBe(false);
  });

  it("disables query when q is undefined", () => {
    const opts = tagSuggestionsQueryOptions(undefined);

    expect(opts.enabled).toBe(false);
  });
});

// =============================================================================
// citiesQueryOptions
// =============================================================================

describe("citiesQueryOptions", () => {
  it("returns correct query key with country", () => {
    const opts = citiesQueryOptions("US");

    expect(opts.queryKey).toEqual(["explore", "cities", "US"]);
  });

  it("uses 30-minute staleTime", () => {
    const opts = citiesQueryOptions("US");

    expect(opts.staleTime).toBe(30 * 60 * 1000);
  });

  it("enables query when country is provided", () => {
    const opts = citiesQueryOptions("US");

    expect(opts.enabled).toBe(true);
  });

  it("disables query when country is empty", () => {
    const opts = citiesQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});
