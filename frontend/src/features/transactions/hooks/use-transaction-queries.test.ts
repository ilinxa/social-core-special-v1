import { describe, it, expect } from "vitest";

import {
  transactionListQueryOptions,
  transactionDetailQueryOptions,
  transactionTypesQueryOptions,
  formMappingsQueryOptions,
  transactionFormResponseQueryOptions,
} from "./use-transaction-queries";

describe("transactionListQueryOptions", () => {
  it("returns correct query key with params", () => {
    const opts = transactionListQueryOptions({ mode: "invitation" });

    expect(opts.queryKey).toEqual([
      "transactions",
      "list",
      { mode: "invitation" },
    ]);
    expect(opts.staleTime).toBe(1 * 60 * 1000);
  });
});

describe("transactionDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = transactionDetailQueryOptions("txn-1");

    expect(opts.queryKey).toEqual(["transactions", "detail", "txn-1"]);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when transactionId is empty", () => {
    const opts = transactionDetailQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

describe("transactionTypesQueryOptions", () => {
  it("returns correct query key with context type", () => {
    const opts = transactionTypesQueryOptions("business");

    expect(opts.queryKey).toEqual(["transactions", "types", "business"]);
    expect(opts.staleTime).toBe(30 * 60 * 1000);
  });

  it("returns query key without context type", () => {
    const opts = transactionTypesQueryOptions();

    expect(opts.queryKey).toEqual(["transactions", "types", undefined]);
  });
});

describe("formMappingsQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = formMappingsQueryOptions("business", "biz-1");

    expect(opts.queryKey).toEqual([
      "transactions",
      "form-mappings",
      "business",
      "biz-1",
    ]);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when accountId is empty", () => {
    const opts = formMappingsQueryOptions("business", "");

    expect(opts.enabled).toBe(false);
  });
});

describe("transactionFormResponseQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = transactionFormResponseQueryOptions("txn-1");

    expect(opts.queryKey).toEqual([
      "transactions",
      "form-response",
      "txn-1",
    ]);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when transactionId is empty", () => {
    const opts = transactionFormResponseQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});
