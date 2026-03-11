import { describe, it, expect } from "vitest";

import { createQueryClient } from "./query-client";
import { ApiError } from "@/lib/api-client";

describe("createQueryClient", () => {
  it("retries on 500 server error", () => {
    const qc = createQueryClient();
    const retryFn = qc.getDefaultOptions().queries?.retry as (
      count: number,
      error: Error,
    ) => boolean;

    expect(typeof retryFn).toBe("function");
    expect(retryFn(0, new ApiError(500, "Server error", "server_error"))).toBe(true);
    expect(retryFn(1, new ApiError(502, "Bad gateway", "server_error"))).toBe(true);
  });

  it("does not retry on permanent client errors (401, 403, 404)", () => {
    const qc = createQueryClient();
    const retryFn = qc.getDefaultOptions().queries?.retry as (
      count: number,
      error: Error,
    ) => boolean;

    expect(retryFn(0, new ApiError(401, "Unauthorized", "authentication_error"))).toBe(false);
    expect(retryFn(0, new ApiError(403, "Forbidden", "permission_denied"))).toBe(false);
    expect(retryFn(0, new ApiError(404, "Not found", "not_found"))).toBe(false);
    expect(retryFn(0, new ApiError(409, "Conflict", "conflict"))).toBe(false);
    expect(retryFn(0, new ApiError(422, "Unprocessable", "validation_error"))).toBe(false);
  });

  it("stops retrying after 3 failures", () => {
    const qc = createQueryClient();
    const retryFn = qc.getDefaultOptions().queries?.retry as (
      count: number,
      error: Error,
    ) => boolean;

    expect(retryFn(3, new ApiError(500, "Server error", "server_error"))).toBe(false);
  });

  it("retries non-ApiError errors", () => {
    const qc = createQueryClient();
    const retryFn = qc.getDefaultOptions().queries?.retry as (
      count: number,
      error: Error,
    ) => boolean;

    expect(retryFn(0, new Error("Network error"))).toBe(true);
  });
});
