import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { ConnectionCard } from "../ConnectionCard";
import type { UserConnectionItem } from "@/types/network";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockConnection: UserConnectionItem = {
  id: "conn-1",
  other_user: {
    id: "user-1",
    username: "jane",
    display_name: "Jane Smith",
    avatar_url: "",
  },
  note: "Hey, let's connect!",
  status: "active",
  connected_at: "2026-02-15T10:00:00Z",
  created_at: "2026-02-10T10:00:00Z",
};

describe("ConnectionCard", () => {
  it("renders user info and note", () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onDisconnect={vi.fn()}
      />,
    );

    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("@jane")).toBeInTheDocument();
    expect(screen.getByText(/Hey, let's connect!/)).toBeInTheDocument();
  });

  it("renders disconnect button", () => {
    render(
      <ConnectionCard
        connection={mockConnection}
        onDisconnect={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Disconnect" })).toBeInTheDocument();
  });

  it("opens confirm dialog and calls onDisconnect", async () => {
    const handleDisconnect = vi.fn();
    const user = userEvent.setup();

    render(
      <ConnectionCard
        connection={mockConnection}
        onDisconnect={handleDisconnect}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Disconnect" }));

    // Dialog should be visible
    expect(screen.getByText("Disconnect?")).toBeInTheDocument();

    // Click confirm
    const confirmBtn = screen.getByRole("button", { name: /Disconnect/i });
    // The dialog has a Disconnect confirm button too — get the one inside dialog
    const buttons = screen.getAllByRole("button", { name: /Disconnect/i });
    await user.click(buttons[buttons.length - 1]);

    expect(handleDisconnect).toHaveBeenCalledWith("conn-1");
  });
});
