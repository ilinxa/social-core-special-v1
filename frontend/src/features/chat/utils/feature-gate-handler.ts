/**
 * Chat Feature Gate Handler
 * =========================
 * Handles 403 FeatureDisabled responses from backend by reactively hiding
 * disabled UI elements. No dedicated gate-check endpoint needed — the error
 * itself is the signal.
 *
 * Backend gates:
 * - systems.chat → entire chat system disabled
 * - user.chat.group → group creation disabled
 * - user.chat.file_sharing → file upload disabled
 * - user.chat.reactions → reactions disabled
 * - user.chat.search → message search disabled
 */

import { ApiError } from "@/lib/api-client";

/** Chat feature flags that can be disabled by backend gates */
export type ChatFeatureFlag =
  | "group"
  | "file_sharing"
  | "reactions"
  | "search"
  | "entity";

/** Session-level set of disabled features (cleared on page reload) */
const disabledFeatures = new Set<ChatFeatureFlag>();

/** Listeners for gate state changes */
const listeners = new Set<() => void>();

/**
 * Check if a 403 error is a FeatureDisabled response and
 * record it if so. Returns true if handled, false otherwise.
 */
export function handleFeatureDisabledError(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  if (error.status !== 403 || error.code !== "feature_disabled") return false;

  // Map backend feature name to our local flag
  const feature = error.details?.feature as string | undefined;
  if (!feature) return false;

  const flag = mapFeatureToFlag(feature);
  if (flag && !disabledFeatures.has(flag)) {
    disabledFeatures.add(flag);
    notifyListeners();
  }

  return true;
}

/**
 * Check if a chat feature is currently known to be disabled.
 */
export function isChatFeatureDisabled(flag: ChatFeatureFlag): boolean {
  return disabledFeatures.has(flag);
}

/**
 * Subscribe to feature gate changes. Returns unsubscribe function.
 */
export function onFeatureGateChange(callback: () => void): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

function notifyListeners() {
  listeners.forEach((cb) => cb());
}

/**
 * Map backend feature path to local flag.
 *
 * Backend sends full paths like "user.chat.group", "business.chat.file_sharing",
 * "platform.chat.entity", etc. We extract the suffix after ".chat." for matching.
 * Also handles short forms ("group", "chat.group") for flexibility.
 */
function mapFeatureToFlag(feature: string): ChatFeatureFlag | null {
  // Extract suffix after ".chat." (e.g., "user.chat.group" → "group")
  const chatMatch = feature.match(/\.chat\.(.+)$/);
  const key = chatMatch ? chatMatch[1] : feature;

  switch (key) {
    case "group":
    case "chat.group":
      return "group";
    case "file_sharing":
    case "chat.file_sharing":
      return "file_sharing";
    case "reactions":
    case "chat.reactions":
      return "reactions";
    case "search":
    case "chat.search":
      return "search";
    case "entity":
    case "chat.entity":
      return "entity";
    default:
      return null;
  }
}
