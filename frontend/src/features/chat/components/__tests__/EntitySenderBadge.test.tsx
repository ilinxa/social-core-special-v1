import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { EntitySenderBadge } from "../EntitySenderBadge";

// =============================================================================
// TESTS
// =============================================================================

describe("EntitySenderBadge", () => {
  it("returns null for user participantType", () => {
    const { container } = render(
      <EntitySenderBadge participantType="user" />,
    );

    expect(container.firstChild).toBeNull();
    expect(
      screen.queryByTestId("entity-sender-badge"),
    ).not.toBeInTheDocument();
  });

  it("renders badge for business participantType", () => {
    render(<EntitySenderBadge participantType="business" />);

    expect(screen.getByTestId("entity-sender-badge")).toBeInTheDocument();
  });

  it("renders badge for platform participantType", () => {
    render(<EntitySenderBadge participantType="platform" />);

    expect(screen.getByTestId("entity-sender-badge")).toBeInTheDocument();
  });

  it("has entity-sender-badge testid", () => {
    render(<EntitySenderBadge participantType="business" />);

    const badge = screen.getByTestId("entity-sender-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.tagName.toLowerCase()).toBe("span");
  });

  it("accepts className prop", () => {
    render(
      <EntitySenderBadge participantType="business" className="ml-2 shrink-0" />,
    );

    const badge = screen.getByTestId("entity-sender-badge");
    expect(badge).toHaveClass("ml-2");
    expect(badge).toHaveClass("shrink-0");
  });

  it("default size is sm (h-4 w-4 badge)", () => {
    render(<EntitySenderBadge participantType="business" />);

    const badge = screen.getByTestId("entity-sender-badge");
    expect(badge).toHaveClass("h-4");
    expect(badge).toHaveClass("w-4");
  });

  it("md size renders h-5 w-5 badge", () => {
    render(<EntitySenderBadge participantType="platform" size="md" />);

    const badge = screen.getByTestId("entity-sender-badge");
    expect(badge).toHaveClass("h-5");
    expect(badge).toHaveClass("w-5");
  });

  it("renders with rounded-full and bg-muted classes", () => {
    render(<EntitySenderBadge participantType="business" />);

    const badge = screen.getByTestId("entity-sender-badge");
    expect(badge).toHaveClass("rounded-full");
    expect(badge).toHaveClass("bg-muted");
  });
});
