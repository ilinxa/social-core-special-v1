"use client";

interface SystemMessageProps {
  content: string;
}

/**
 * Centered, muted text for system events (joined, left, promoted, etc.).
 */
export function SystemMessage({ content }: SystemMessageProps) {
  return (
    <div className="flex justify-center py-1.5">
      <span className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
        {content}
      </span>
    </div>
  );
}
