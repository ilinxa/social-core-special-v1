"use client";

/**
 * Full-height wrapper that negates the parent <main> padding.
 *
 * The (app) layout renders:
 *   <main className="flex-1 overflow-y-auto p-6 pb-20 md:pb-6">
 *
 * Chat needs full-height with its own scroll management.
 * This wrapper uses absolute positioning to fill the parent completely.
 */
export function ChatLayoutWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute inset-0 flex flex-col overflow-hidden">
      {children}
    </div>
  );
}
