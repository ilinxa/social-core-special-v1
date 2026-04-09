import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ScopeTabBar } from "../ScopeTabBar";

describe("ScopeTabBar", () => {
  it("renders both tabs when showEntityInbox is true", () => {
    const onTabChange = vi.fn();
    render(
      <ScopeTabBar
        activeTab="internal"
        onTabChange={onTabChange}
        showEntityInbox={true}
      />
    );

    expect(screen.getByRole("tab", { name: /internal/i })).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: /entity inbox/i })
    ).toBeInTheDocument();
  });

  it("returns null when showEntityInbox is false", () => {
    const onTabChange = vi.fn();
    const { container } = render(
      <ScopeTabBar
        activeTab="internal"
        onTabChange={onTabChange}
        showEntityInbox={false}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it("calls onTabChange when clicking a tab", async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();

    render(
      <ScopeTabBar
        activeTab="internal"
        onTabChange={onTabChange}
        showEntityInbox={true}
      />
    );

    const inboxTab = screen.getByRole("tab", { name: /entity inbox/i });
    await user.click(inboxTab);

    expect(onTabChange).toHaveBeenCalledWith("inbox");
  });

  it("highlights the active tab", () => {
    const onTabChange = vi.fn();

    const { rerender } = render(
      <ScopeTabBar
        activeTab="internal"
        onTabChange={onTabChange}
        showEntityInbox={true}
      />
    );

    // Check internal tab is active
    const internalTab = screen.getByRole("tab", { name: /internal/i });
    expect(internalTab).toHaveAttribute("data-state", "active");

    // Switch to inbox tab
    rerender(
      <ScopeTabBar
        activeTab="inbox"
        onTabChange={onTabChange}
        showEntityInbox={true}
      />
    );

    // Check inbox tab is now active
    const inboxTab = screen.getByRole("tab", { name: /entity inbox/i });
    expect(inboxTab).toHaveAttribute("data-state", "active");
  });
});
