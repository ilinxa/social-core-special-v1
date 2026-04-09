/**
 * CMS Feature Gate Hook
 * ======================
 * Reactive hook for CMS feature gate state.
 * Uses useSyncExternalStore for tear-free reads.
 *
 * Pattern: same as features/chat/hooks/use-chat-feature-gate.ts
 */

"use client";

import { useSyncExternalStore } from "react";

import type { CmsFeatureFlag } from "@/features/cms/utils/cms-feature-gate-handler";
import {
  getCmsFeatureServerSnapshot,
  getCmsFeatureSnapshot,
  onCmsFeatureGateChange,
} from "@/features/cms/utils/cms-feature-gate-handler";

/**
 * Returns true if the CMS feature flag is enabled (not detected as disabled).
 * Reactively updates when a 403 feature_disabled response is received.
 */
export function useCmsFeatureEnabled(flag: CmsFeatureFlag): boolean {
  const disabledSet = useSyncExternalStore(
    onCmsFeatureGateChange,
    getCmsFeatureSnapshot,
    getCmsFeatureServerSnapshot,
  );
  return !disabledSet.has(flag);
}
