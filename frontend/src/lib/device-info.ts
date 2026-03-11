/**
 * Device identification for session tracking.
 *
 * Generates a persistent device ID (UUID stored in localStorage)
 * so the backend can track sessions per-device rather than creating
 * a new session on every login from the same browser.
 */

const DEVICE_ID_KEY = "device_id";

/**
 * Get or create a persistent device ID for this browser.
 * Returns a stable UUID that persists across sessions.
 */
export function getDeviceId(): string {
  if (typeof window === "undefined") return "ssr";

  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id =
      typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : // Fallback for older browsers / non-secure contexts
          "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
            const r = (Math.random() * 16) | 0;
            return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
          });
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

/**
 * Build device info object for auth API calls.
 */
export function getDeviceInfo(): {
  device_id: string;
  device_type: "web";
  device_name: string;
} {
  return {
    device_id: getDeviceId(),
    device_type: "web",
    device_name: typeof navigator !== "undefined" ? navigator.userAgent : "",
  };
}
