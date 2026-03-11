import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge, type StatusConfig } from "./StatusBadge";

type TestStatus = "active" | "suspended" | "banned";

const statusMap: Record<TestStatus, StatusConfig> = {
  active: { label: "Active", className: "bg-green-100 text-green-800" },
  suspended: { label: "Suspended", className: "bg-yellow-100 text-yellow-800" },
  banned: { label: "Banned", className: "bg-red-100 text-red-800" },
};

describe("StatusBadge", () => {
  it("renders the correct label for a status", () => {
    render(<StatusBadge status="active" statusMap={statusMap} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies status-specific className", () => {
    render(<StatusBadge status="suspended" statusMap={statusMap} />);
    const badge = screen.getByText("Suspended");
    expect(badge.className).toContain("bg-yellow-100");
    expect(badge.className).toContain("text-yellow-800");
  });

  it("renders raw status text for unknown statuses", () => {
    render(
      <StatusBadge
        status={"unknown" as TestStatus}
        statusMap={statusMap}
      />,
    );
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });

  it("applies additional className", () => {
    render(
      <StatusBadge
        status="active"
        statusMap={statusMap}
        className="ml-2"
      />,
    );
    const badge = screen.getByText("Active");
    expect(badge.className).toContain("ml-2");
  });

  it("renders each status correctly", () => {
    const { unmount: u1 } = render(
      <StatusBadge status="active" statusMap={statusMap} />,
    );
    expect(screen.getByText("Active")).toBeInTheDocument();
    u1();

    const { unmount: u2 } = render(
      <StatusBadge status="suspended" statusMap={statusMap} />,
    );
    expect(screen.getByText("Suspended")).toBeInTheDocument();
    u2();

    render(<StatusBadge status="banned" statusMap={statusMap} />);
    expect(screen.getByText("Banned")).toBeInTheDocument();
  });
});
