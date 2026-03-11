import { describe, it, expect, vi, beforeEach } from "vitest";

import { handleApiError } from "./api-error-handler";
import { ApiError } from "./api-client";

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}));

vi.mock("./error-reporting", () => ({
  reportError: vi.fn(),
}));

import { toast } from "sonner";
import { reportError } from "./error-reporting";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("handleApiError", () => {
  it("maps validation errors to form fields via setError", () => {
    const setError = vi.fn();
    const error = new ApiError(400, "Validation failed", "validation_error", {
      email: ["Invalid email format"],
      password: ["Too short"],
    });

    handleApiError(error, { setError });

    expect(setError).toHaveBeenCalledWith("email", { message: "Invalid email format" });
    expect(setError).toHaveBeenCalledWith("password", { message: "Too short" });
  });

  it("calls custom handler when error code matches", () => {
    const handler = vi.fn();
    const error = new ApiError(401, "Bad credentials", "invalid_credentials");

    handleApiError(error, {
      handlers: { invalid_credentials: handler },
    });

    expect(handler).toHaveBeenCalledWith(error);
  });

  it("handles rate limiting with retry-after", () => {
    const setError = vi.fn();
    const error = new ApiError(429, "Too many requests", "rate_limit_exceeded", {
      retry_after: 30,
    });

    handleApiError(error, { setError });

    expect(setError).toHaveBeenCalledWith("root", {
      message: "Too many attempts. Try again in 30 seconds.",
    });
  });

  it("falls back to root error for unhandled ApiError", () => {
    const setError = vi.fn();
    const error = new ApiError(500, "Server error", "server_error");

    handleApiError(error, { setError });

    expect(setError).toHaveBeenCalledWith("root", { message: "Server error" });
  });

  it("shows toast for non-ApiError when showToast is true", () => {
    handleApiError(new Error("network failure"), { showToast: true });

    expect(toast.error).toHaveBeenCalledWith("An unexpected error occurred");
    expect(reportError).toHaveBeenCalled();
  });

  it("reports non-ApiError and sets root form error", () => {
    const setError = vi.fn();
    handleApiError(new TypeError("null ref"), { setError });

    expect(reportError).toHaveBeenCalled();
    expect(setError).toHaveBeenCalledWith("root", { message: "An unexpected error occurred" });
  });
});
