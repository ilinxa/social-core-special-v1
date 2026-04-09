"use client";

import { Separator } from "@/components/ui/separator";

interface DateSeparatorProps {
  date: string;
}

/**
 * Renders a date divider between messages from different days.
 * Formats: "Today", "Yesterday", or "Mon, Jan 1, 2026".
 */
export function DateSeparator({ date }: DateSeparatorProps) {
  return (
    <div className="flex items-center gap-3 py-3">
      <Separator className="flex-1" />
      <span className="shrink-0 text-xs font-medium text-muted-foreground">
        {formatDateLabel(date)}
      </span>
      <Separator className="flex-1" />
    </div>
  );
}

function formatDateLabel(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();

  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isToday) return "Today";

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate();

  if (isYesterday) return "Yesterday";

  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}
