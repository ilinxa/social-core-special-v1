import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SystemMessage } from "../SystemMessage";

describe("SystemMessage", () => {
  it("renders the content text", () => {
    render(<SystemMessage content="Alice joined the conversation" />);

    expect(screen.getByText("Alice joined the conversation")).toBeInTheDocument();
  });

  it("has muted foreground styling", () => {
    render(<SystemMessage content="Bob left the conversation" />);

    const element = screen.getByText("Bob left the conversation");
    expect(element).toHaveClass("text-muted-foreground");
  });
});
