import { useCallback, useSyncExternalStore } from "react";

import {
  isChatFeatureDisabled,
  onFeatureGateChange,
  type ChatFeatureFlag,
} from "@/features/chat/utils/feature-gate-handler";

/**
 * Hook that reactively checks if a chat feature is disabled.
 * Returns true when the feature is available (not disabled).
 *
 * Usage:
 *   const canSearch = useChatFeatureEnabled("search");
 *   if (!canSearch) return null; // hide search button
 */
export function useChatFeatureEnabled(flag: ChatFeatureFlag): boolean {
  const subscribe = useCallback(
    (cb: () => void) => onFeatureGateChange(cb),
    [],
  );
  const getSnapshot = useCallback(() => !isChatFeatureDisabled(flag), [flag]);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
