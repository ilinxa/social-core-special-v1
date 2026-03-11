import { describe, it, expect } from "vitest";

import {
  templateListQueryOptions,
  templateDetailQueryOptions,
  libraryQueryOptions,
  responseListQueryOptions,
  responseDetailQueryOptions,
  myResponsesQueryOptions,
} from "./use-form-queries";

describe("templateListQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = templateListQueryOptions("business", "acc-1");

    expect(opts.queryKey).toEqual(["forms", "templates", "business", "acc-1"]);
    expect(opts.staleTime).toBe(2 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when accountId is empty", () => {
    const opts = templateListQueryOptions("business", "");

    expect(opts.enabled).toBe(false);
  });
});

describe("templateDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = templateDetailQueryOptions("tpl-1");

    expect(opts.queryKey).toEqual(["forms", "detail", "tpl-1"]);
    expect(opts.staleTime).toBe(2 * 60 * 1000);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when formId is empty", () => {
    const opts = templateDetailQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

describe("libraryQueryOptions", () => {
  it("returns correct query key with 5min stale time", () => {
    const opts = libraryQueryOptions();

    expect(opts.queryKey).toEqual(["forms", "library"]);
    expect(opts.staleTime).toBe(5 * 60 * 1000);
  });
});

describe("responseListQueryOptions", () => {
  it("returns correct query key with params", () => {
    const opts = responseListQueryOptions("tpl-1", { status: "submitted" });

    expect(opts.queryKey).toEqual([
      "forms",
      "responses",
      "tpl-1",
      { status: "submitted" },
    ]);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when formId is empty", () => {
    const opts = responseListQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

describe("responseDetailQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = responseDetailQueryOptions("resp-1");

    expect(opts.queryKey).toEqual(["forms", "response-detail", "resp-1"]);
    expect(opts.enabled).toBe(true);
  });

  it("disables query when responseId is empty", () => {
    const opts = responseDetailQueryOptions("");

    expect(opts.enabled).toBe(false);
  });
});

describe("myResponsesQueryOptions", () => {
  it("returns correct query key", () => {
    const opts = myResponsesQueryOptions();

    expect(opts.queryKey).toEqual(["forms", "my-responses"]);
    expect(opts.staleTime).toBe(2 * 60 * 1000);
  });
});
