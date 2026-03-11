"use client";

import { TRANSACTION_STATUS_CONFIG } from "@/features/transactions/constants/transaction-statuses";
import type { TransactionLog } from "@/types/transactions";

interface TransactionTimelineProps {
  logs: TransactionLog[];
}

export function TransactionTimeline({ logs }: TransactionTimelineProps) {
  if (!logs.length) {
    return (
      <p className="text-sm text-muted-foreground">No activity recorded.</p>
    );
  }

  const sortedLogs = [...logs].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Activity</h3>
      <ol className="relative border-l border-muted-foreground/20 space-y-4 pl-4">
        {sortedLogs.map((log) => {
          const statusLabel = log.new_status
            ? TRANSACTION_STATUS_CONFIG[log.new_status]?.label ?? log.new_status
            : log.event_type;

          return (
            <li key={log.id} className="relative">
              <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full border border-background bg-muted-foreground/50" />
              <div className="space-y-1">
                <p className="text-sm font-medium">{statusLabel}</p>
                {log.previous_status && (
                  <p className="text-xs text-muted-foreground">
                    From: {TRANSACTION_STATUS_CONFIG[log.previous_status]?.label ?? log.previous_status}
                  </p>
                )}
                <time className="text-xs text-muted-foreground">
                  {new Date(log.timestamp).toLocaleString()}
                </time>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
