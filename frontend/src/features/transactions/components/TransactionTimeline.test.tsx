import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { TransactionTimeline } from "./TransactionTimeline";
import type { TransactionLog } from "@/types/transactions";

const mockLogs: TransactionLog[] = [
  {
    id: "log-1",
    event_type: "status_change",
    timestamp: "2026-01-15T10:00:00Z",
    previous_status: null,
    new_status: "created",
    metadata: {},
  },
  {
    id: "log-2",
    event_type: "status_change",
    timestamp: "2026-01-15T11:00:00Z",
    previous_status: "created",
    new_status: "pending",
    metadata: {},
  },
  {
    id: "log-3",
    event_type: "status_change",
    timestamp: "2026-01-15T12:00:00Z",
    previous_status: "pending",
    new_status: "accepted",
    metadata: {},
  },
];

describe("TransactionTimeline", () => {
  it("renders empty message when no logs", () => {
    render(<TransactionTimeline logs={[]} />);
    expect(screen.getByText("No activity recorded.")).toBeInTheDocument();
  });

  it("renders activity heading", () => {
    render(<TransactionTimeline logs={mockLogs} />);
    expect(screen.getByText("Activity")).toBeInTheDocument();
  });

  it("renders all log entries", () => {
    render(<TransactionTimeline logs={mockLogs} />);
    expect(screen.getByText("Created")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Accepted")).toBeInTheDocument();
  });

  it("shows previous status for transitions", () => {
    render(<TransactionTimeline logs={mockLogs} />);
    // log-2: From: Created → Pending
    expect(screen.getByText(/From: Created/)).toBeInTheDocument();
  });

  it("renders timestamps", () => {
    render(<TransactionTimeline logs={mockLogs} />);
    // Should render 3 timestamps
    const timestamps = screen.getAllByText(/2026/);
    expect(timestamps.length).toBeGreaterThanOrEqual(3);
  });
});
