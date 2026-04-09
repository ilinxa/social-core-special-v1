import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReactionPicker } from "../ReactionPicker";
import type { ReactionType } from "@/features/chat/types";

describe("ReactionPicker", () => {
  const mockOnSelect = vi.fn();
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 6 reaction buttons when open", () => {
    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.getByTestId("reaction-picker")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-like")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-heart")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-laugh")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-wow")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-sad")).toBeInTheDocument();
    expect(screen.getByTestId("reaction-angry")).toBeInTheDocument();
  });

  it("renders trigger element", () => {
    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
      />
    );

    expect(screen.getByRole("button", { name: "React" })).toBeInTheDocument();
  });

  it("calls onSelect with correct reaction type on click", async () => {
    const user = userEvent.setup();

    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const likeButton = screen.getByTestId("reaction-like");
    await user.click(likeButton);

    expect(mockOnSelect).toHaveBeenCalledWith("like");
    expect(mockOnSelect).toHaveBeenCalledTimes(1);
  });

  it("calls onOpenChange(false) after selection", async () => {
    const user = userEvent.setup();

    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const heartButton = screen.getByTestId("reaction-heart");
    await user.click(heartButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    expect(mockOnOpenChange).toHaveBeenCalledTimes(1);
  });

  it("calls onSelect with different reaction types correctly", async () => {
    const user = userEvent.setup();

    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const reactions: ReactionType[] = [
      "like",
      "heart",
      "laugh",
      "wow",
      "sad",
      "angry",
    ];

    for (const reaction of reactions) {
      const button = screen.getByTestId(`reaction-${reaction}`);
      await user.click(button);
      expect(mockOnSelect).toHaveBeenCalledWith(reaction);
      mockOnSelect.mockClear();
    }
  });

  it("picker content has correct testid", () => {
    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={true}
        onOpenChange={mockOnOpenChange}
      />
    );

    const picker = screen.getByTestId("reaction-picker");
    expect(picker).toBeInTheDocument();
  });

  it("does not render picker content when closed", () => {
    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
        open={false}
        onOpenChange={mockOnOpenChange}
      />
    );

    expect(screen.queryByTestId("reaction-picker")).not.toBeInTheDocument();
  });

  it("renders picker content when no open prop provided and trigger is clicked", async () => {
    const user = userEvent.setup();

    render(
      <ReactionPicker
        onSelect={mockOnSelect}
        trigger={<button>React</button>}
      />
    );

    const trigger = screen.getByRole("button", { name: "React" });
    await user.click(trigger);

    expect(screen.getByTestId("reaction-picker")).toBeInTheDocument();
  });
});
