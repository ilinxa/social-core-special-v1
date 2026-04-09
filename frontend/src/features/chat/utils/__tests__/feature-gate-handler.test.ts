import { describe, it, expect, vi, beforeEach } from "vitest";

import type { ApiError as ApiErrorClass } from "@/lib/api-client";
import type {
  handleFeatureDisabledError as HandleFn,
  isChatFeatureDisabled as IsDisabledFn,
  onFeatureGateChange as OnChangeFn,
} from "../feature-gate-handler";

// =============================================================================
// Module-level state reset
// =============================================================================
// The feature-gate-handler module maintains a module-level Set of disabled
// features. We use vi.resetModules() + dynamic imports so each describe block
// starts with a fresh module instance.
//
// IMPORTANT: ApiError must also be dynamically imported after resetModules,
// because the re-imported feature-gate-handler gets its own ApiError class
// and instanceof checks fail across module reset boundaries.

// =============================================================================
// TESTS — handleFeatureDisabledError
// =============================================================================

describe("handleFeatureDisabledError", () => {
  let handleFeatureDisabledError: typeof HandleFn;
  let ApiError: typeof ApiErrorClass;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../feature-gate-handler");
    const apiMod = await import("@/lib/api-client");
    handleFeatureDisabledError = mod.handleFeatureDisabledError;
    ApiError = apiMod.ApiError;
  });

  it("returns false for non-ApiError", () => {
    expect(handleFeatureDisabledError(new Error("generic"))).toBe(false);
  });

  it("returns false for ApiError with 404 status", () => {
    const error = new ApiError(404, "Not found", "not_found");
    expect(handleFeatureDisabledError(error)).toBe(false);
  });

  it("returns false for 403 with non-feature_disabled code", () => {
    const error = new ApiError(403, "Forbidden", "permission_denied");
    expect(handleFeatureDisabledError(error)).toBe(false);
  });

  it("returns false for 403 feature_disabled without feature in details", () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {});
    expect(handleFeatureDisabledError(error)).toBe(false);
  });

  it("returns true for valid feature_disabled error with known feature", () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "group",
    });
    expect(handleFeatureDisabledError(error)).toBe(true);
  });

  it("returns true for unknown feature name but does not record it", () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "unknown_feature_xyz",
    });
    expect(handleFeatureDisabledError(error)).toBe(true);
  });
});

// =============================================================================
// TESTS — isChatFeatureDisabled
// =============================================================================

describe("isChatFeatureDisabled", () => {
  let handleFeatureDisabledError: typeof HandleFn;
  let isChatFeatureDisabled: typeof IsDisabledFn;
  let ApiError: typeof ApiErrorClass;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../feature-gate-handler");
    const apiMod = await import("@/lib/api-client");
    handleFeatureDisabledError = mod.handleFeatureDisabledError;
    isChatFeatureDisabled = mod.isChatFeatureDisabled;
    ApiError = apiMod.ApiError;
  });

  it("returns false initially for all features", () => {
    expect(isChatFeatureDisabled("group")).toBe(false);
    expect(isChatFeatureDisabled("file_sharing")).toBe(false);
    expect(isChatFeatureDisabled("reactions")).toBe(false);
    expect(isChatFeatureDisabled("search")).toBe(false);
    expect(isChatFeatureDisabled("entity")).toBe(false);
  });

  it("returns true after handleFeatureDisabledError records a feature", () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "group",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("group")).toBe(true);
    // Other features remain unaffected
    expect(isChatFeatureDisabled("file_sharing")).toBe(false);
  });
});

// =============================================================================
// TESTS — Feature name mapping
// =============================================================================

describe("feature name mapping", () => {
  let handleFeatureDisabledError: typeof HandleFn;
  let isChatFeatureDisabled: typeof IsDisabledFn;
  let ApiError: typeof ApiErrorClass;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../feature-gate-handler");
    const apiMod = await import("@/lib/api-client");
    handleFeatureDisabledError = mod.handleFeatureDisabledError;
    isChatFeatureDisabled = mod.isChatFeatureDisabled;
    ApiError = apiMod.ApiError;
  });

  it('maps "user.chat.group" to "group" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "user.chat.group",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("group")).toBe(true);
  });

  it('maps "business.chat.group" to "group" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "business.chat.group",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("group")).toBe(true);
  });

  it('maps "user.chat.reactions" to "reactions" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "user.chat.reactions",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("reactions")).toBe(true);
  });

  it('maps "user.chat.file_sharing" to "file_sharing" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "user.chat.file_sharing",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("file_sharing")).toBe(true);
  });

  it('maps "user.chat.search" to "search" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "user.chat.search",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("search")).toBe(true);
  });

  it('maps "business.chat.entity" to "entity" flag', () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "business.chat.entity",
    });
    handleFeatureDisabledError(error);

    expect(isChatFeatureDisabled("entity")).toBe(true);
  });

  it("does not record unknown feature names", () => {
    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "totally_unknown",
    });
    handleFeatureDisabledError(error);

    // None of the known flags should be set
    expect(isChatFeatureDisabled("group")).toBe(false);
    expect(isChatFeatureDisabled("file_sharing")).toBe(false);
    expect(isChatFeatureDisabled("reactions")).toBe(false);
    expect(isChatFeatureDisabled("search")).toBe(false);
    expect(isChatFeatureDisabled("entity")).toBe(false);
  });
});

// =============================================================================
// TESTS — onFeatureGateChange
// =============================================================================

describe("onFeatureGateChange", () => {
  let handleFeatureDisabledError: typeof HandleFn;
  let onFeatureGateChange: typeof OnChangeFn;
  let ApiError: typeof ApiErrorClass;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../feature-gate-handler");
    const apiMod = await import("@/lib/api-client");
    handleFeatureDisabledError = mod.handleFeatureDisabledError;
    onFeatureGateChange = mod.onFeatureGateChange;
    ApiError = apiMod.ApiError;
  });

  it("calls callback when a feature gets disabled", () => {
    const callback = vi.fn();
    onFeatureGateChange(callback);

    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "search",
    });
    handleFeatureDisabledError(error);

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("returns unsubscribe function that stops callbacks", () => {
    const callback = vi.fn();
    const unsubscribe = onFeatureGateChange(callback);

    unsubscribe();

    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "reactions",
    });
    handleFeatureDisabledError(error);

    expect(callback).not.toHaveBeenCalled();
  });

  it("does not notify when same feature is disabled twice", () => {
    const callback = vi.fn();
    onFeatureGateChange(callback);

    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "group",
    });
    handleFeatureDisabledError(error);
    handleFeatureDisabledError(error);

    // Only called once because the second time the feature is already in the Set
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("does not notify for unknown features", () => {
    const callback = vi.fn();
    onFeatureGateChange(callback);

    const error = new ApiError(403, "Disabled", "feature_disabled", {
      feature: "unknown_thing",
    });
    handleFeatureDisabledError(error);

    // mapFeatureToFlag returns null, so flag is null and notifyListeners is not called
    expect(callback).not.toHaveBeenCalled();
  });
});
