/**
 * CMS Feature Gate Handler
 * =========================
 * Detects disabled CMS features from 403 responses and records them
 * in a session-level Set for reactive UI hiding.
 *
 * Pattern: same as features/chat/utils/feature-gate-handler.ts
 */

import { ApiError } from "@/lib/api-client";

// =============================================================================
// TYPES
// =============================================================================

export type CmsFeatureFlag = "business_cms" | "activation_request";

// =============================================================================
// STATE
// =============================================================================

const disabledFeatures = new Set<CmsFeatureFlag>();
const listeners = new Set<() => void>();

// =============================================================================
// FEATURE → FLAG MAPPING
// =============================================================================

const FEATURE_PATH_TO_FLAG: Record<string, CmsFeatureFlag> = {
  "business.cms.enabled": "business_cms",
  "business.cms": "business_cms",
  "business.cms.activation_request": "activation_request",
};

// =============================================================================
// PUBLIC API
// =============================================================================

/**
 * Handle a potential feature-disabled error from a CMS API call.
 * Returns true if the error was a feature gate (handled), false otherwise.
 */
export function handleCmsFeatureDisabledError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  if (error.status !== 403) return false;
  if (error.code !== "feature_disabled") return false;

  const featurePath = error.details?.feature as string | undefined;
  if (!featurePath) return false;

  const flag = FEATURE_PATH_TO_FLAG[featurePath];
  if (!flag) return false;

  if (!disabledFeatures.has(flag)) {
    disabledFeatures.add(flag);
    listeners.forEach((cb) => cb());
  }

  return true;
}

/**
 * Check if a CMS feature is disabled (detected via 403 in this session).
 */
export function isCmsFeatureDisabled(flag: CmsFeatureFlag): boolean {
  return disabledFeatures.has(flag);
}

/**
 * Subscribe to feature gate changes. Returns unsubscribe function.
 */
export function onCmsFeatureGateChange(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

/**
 * Get the current snapshot for useSyncExternalStore (SSR-safe).
 */
export function getCmsFeatureSnapshot(): ReadonlySet<CmsFeatureFlag> {
  return disabledFeatures;
}

/**
 * Server snapshot — assume all features enabled during SSR.
 */
export function getCmsFeatureServerSnapshot(): ReadonlySet<CmsFeatureFlag> {
  return new Set();
}
