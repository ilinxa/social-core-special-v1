/**
 * CMS Feature Gate Handler Tests
 * ================================
 * Tests for feature gate detection, storage, and subscription.
 *
 * Uses vi.resetModules() + dynamic import to reset module-level Set state.
 * ApiError must also be dynamically imported after reset (instanceof boundary).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

import type { ApiError as ApiErrorClass } from "@/lib/api-client";
import type {
  handleCmsFeatureDisabledError as HandleFn,
  isCmsFeatureDisabled as IsDisabledFn,
  onCmsFeatureGateChange as OnChangeFn,
  getCmsFeatureServerSnapshot as GetServerFn,
} from "../cms-feature-gate-handler";

describe("handleCmsFeatureDisabledError", () => {
  let handleCmsFeatureDisabledError: typeof HandleFn;
  let isCmsFeatureDisabled: typeof IsDisabledFn;
  let onCmsFeatureGateChange: typeof OnChangeFn;
  let ApiError: typeof ApiErrorClass;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../cms-feature-gate-handler");
    const apiMod = await import("@/lib/api-client");
    handleCmsFeatureDisabledError = mod.handleCmsFeatureDisabledError;
    isCmsFeatureDisabled = mod.isCmsFeatureDisabled;
    onCmsFeatureGateChange = mod.onCmsFeatureGateChange;
    ApiError = apiMod.ApiError;
  });

  it("returns false for non-ApiError", () => {
    expect(handleCmsFeatureDisabledError(new Error("oops"))).toBe(false);
  });

  it("returns false for non-403 ApiError", () => {
    const error = new ApiError(404, "Not found", "not_found");
    expect(handleCmsFeatureDisabledError(error)).toBe(false);
  });

  it("returns false for 403 without feature_disabled code", () => {
    const error = new ApiError(403, "Forbidden", "permission_denied");
    expect(handleCmsFeatureDisabledError(error)).toBe(false);
  });

  it("detects business.cms.enabled and records business_cms flag", () => {
    const error = new ApiError(403, "Feature disabled", "feature_disabled", {
      feature: "business.cms.enabled",
    });
    expect(handleCmsFeatureDisabledError(error)).toBe(true);
    expect(isCmsFeatureDisabled("business_cms")).toBe(true);
  });

  it("detects business.cms.activation_request flag", () => {
    const error = new ApiError(403, "Feature disabled", "feature_disabled", {
      feature: "business.cms.activation_request",
    });
    expect(handleCmsFeatureDisabledError(error)).toBe(true);
    expect(isCmsFeatureDisabled("activation_request")).toBe(true);
  });

  it("fires listeners on new flag", () => {
    const listener = vi.fn();
    onCmsFeatureGateChange(listener);

    const error = new ApiError(403, "Feature disabled", "feature_disabled", {
      feature: "business.cms.enabled",
    });
    handleCmsFeatureDisabledError(error);
    expect(listener).toHaveBeenCalledOnce();
  });

  it("does not fire listener on duplicate flag", () => {
    const error = new ApiError(403, "Feature disabled", "feature_disabled", {
      feature: "business.cms.enabled",
    });
    handleCmsFeatureDisabledError(error);

    const listener = vi.fn();
    onCmsFeatureGateChange(listener);
    handleCmsFeatureDisabledError(error);
    expect(listener).not.toHaveBeenCalled();
  });

  it("unsubscribe prevents callback", () => {
    const listener = vi.fn();
    const unsub = onCmsFeatureGateChange(listener);
    unsub();

    const error = new ApiError(403, "Feature disabled", "feature_disabled", {
      feature: "business.cms.enabled",
    });
    handleCmsFeatureDisabledError(error);
    expect(listener).not.toHaveBeenCalled();
  });
});

describe("getCmsFeatureServerSnapshot", () => {
  let getCmsFeatureServerSnapshot: typeof GetServerFn;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("../cms-feature-gate-handler");
    getCmsFeatureServerSnapshot = mod.getCmsFeatureServerSnapshot;
  });

  it("returns empty set for SSR", () => {
    expect(getCmsFeatureServerSnapshot().size).toBe(0);
  });
});
