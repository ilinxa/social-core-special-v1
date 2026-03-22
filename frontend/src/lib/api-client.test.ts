import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

import {
  ApiError,
  setAccessToken,
  getAccessToken,
  clearTokens,
  scheduleProactiveRefresh,
  cancelProactiveRefresh,
} from "@/lib/api-client";

// =============================================================================
// ApiError class
// =============================================================================

describe("ApiError", () => {
  it("has correct properties", () => {
    const details = { field: "email" };
    const error = new ApiError(400, "Bad request", "validation_error", details);

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe("ApiError");
    expect(error.status).toBe(400);
    expect(error.message).toBe("Bad request");
    expect(error.code).toBe("validation_error");
    expect(error.details).toEqual(details);
  });

  it("isNotFound returns true for 404", () => {
    const error = new ApiError(404, "Not found", "not_found");
    expect(error.isNotFound).toBe(true);
    expect(error.isUnauthorized).toBe(false);
  });

  it("isUnauthorized returns true for 401", () => {
    const error = new ApiError(401, "Unauthorized", "token_expired");
    expect(error.isUnauthorized).toBe(true);
    expect(error.isNotFound).toBe(false);
  });

  it("isRateLimited returns true for 429 and exposes retryAfter", () => {
    const error = new ApiError(429, "Too many requests", "rate_limited", {
      retry_after: 30,
    });

    expect(error.isRateLimited).toBe(true);
    expect(error.retryAfter).toBe(30);
  });

  it("isValidation returns true for status 400 with validation_error code", () => {
    const error = new ApiError(400, "Validation failed", "validation_error", {
      email: ["This field is required"],
    });

    expect(error.isValidation).toBe(true);

    // A 400 with a different code should not be a validation error
    const otherError = new ApiError(400, "Bad request", "bad_request");
    expect(otherError.isValidation).toBe(false);
  });

  it("isConflict returns true for 409", () => {
    const error = new ApiError(409, "Conflict", "duplicate");
    expect(error.isConflict).toBe(true);
    expect(error.isNotFound).toBe(false);
  });

  it("isForbidden returns true for 403", () => {
    const error = new ApiError(403, "Forbidden", "permission_denied");
    expect(error.isForbidden).toBe(true);
    expect(error.isUnauthorized).toBe(false);
  });
});

// =============================================================================
// Token management
// =============================================================================

describe("Token management", () => {
  beforeEach(() => {
    clearTokens();
  });

  it("setAccessToken / getAccessToken round-trip", () => {
    expect(getAccessToken()).toBeNull();

    setAccessToken("test-jwt-token-123");
    expect(getAccessToken()).toBe("test-jwt-token-123");
  });

  it("clearTokens clears the access token", () => {
    setAccessToken("token-to-clear");
    expect(getAccessToken()).toBe("token-to-clear");

    clearTokens();
    expect(getAccessToken()).toBeNull();
  });
});

// =============================================================================
// Proactive token refresh
// =============================================================================

describe("Proactive refresh scheduling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    cancelProactiveRefresh();
  });

  afterEach(() => {
    cancelProactiveRefresh();
    vi.useRealTimers();
  });

  it("scheduleProactiveRefresh sets a timer at 80% of lifetime", () => {
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");

    scheduleProactiveRefresh(100); // 100 seconds → 80s = 80000ms

    expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 80000);
    setTimeoutSpy.mockRestore();
  });

  it("cancelProactiveRefresh clears the timer", () => {
    const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");

    scheduleProactiveRefresh(100);
    cancelProactiveRefresh();

    expect(clearTimeoutSpy).toHaveBeenCalled();
    clearTimeoutSpy.mockRestore();
  });

  it("clearTokens cancels proactive refresh", () => {
    const clearTimeoutSpy = vi.spyOn(globalThis, "clearTimeout");

    scheduleProactiveRefresh(100);
    clearTokens();

    expect(clearTimeoutSpy).toHaveBeenCalled();
    clearTimeoutSpy.mockRestore();
  });

  it("ignores non-positive expiresInSeconds", () => {
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    const callCountBefore = setTimeoutSpy.mock.calls.length;

    scheduleProactiveRefresh(0);
    scheduleProactiveRefresh(-1);

    expect(setTimeoutSpy.mock.calls.length).toBe(callCountBefore);
    setTimeoutSpy.mockRestore();
  });
});
