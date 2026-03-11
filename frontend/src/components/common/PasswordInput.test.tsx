import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { PasswordInput } from "./PasswordInput";

describe("PasswordInput", () => {
  it("renders as password input by default", () => {
    render(<PasswordInput aria-label="Password" />);

    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");
  });

  it("toggles to text input when show button is clicked", () => {
    render(<PasswordInput aria-label="Password" />);

    const toggle = screen.getByRole("button", { name: "Show password" });
    fireEvent.click(toggle);

    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "text");
  });

  it("toggles back to password input on second click", () => {
    render(<PasswordInput aria-label="Password" />);

    const toggle = screen.getByRole("button", { name: "Show password" });
    fireEvent.click(toggle);

    const hideToggle = screen.getByRole("button", { name: "Hide password" });
    fireEvent.click(hideToggle);

    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");
  });

  it("toggle button is keyboard accessible (no tabIndex restriction)", () => {
    render(<PasswordInput aria-label="Password" />);

    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle).not.toHaveAttribute("tabindex", "-1");
  });
});
