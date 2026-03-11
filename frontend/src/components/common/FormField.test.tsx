import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { FormField } from "./FormField";

describe("FormField", () => {
  it("renders label and input", () => {
    render(<FormField label="Email" name="email" />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("shows error message when error prop provided", () => {
    render(
      <FormField
        label="Email"
        name="email"
        error={{ type: "required", message: "Email is required" }}
      />,
    );

    expect(screen.getByText("Email is required")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows description text when no error", () => {
    render(
      <FormField label="Email" name="email" description="Enter your email address" />,
    );

    expect(screen.getByText("Enter your email address")).toBeInTheDocument();
  });

  it("hides description when error is shown", () => {
    render(
      <FormField
        label="Email"
        name="email"
        description="Enter your email address"
        error={{ type: "required", message: "Email is required" }}
      />,
    );

    expect(screen.getByText("Email is required")).toBeInTheDocument();
    expect(screen.queryByText("Enter your email address")).not.toBeInTheDocument();
  });

  it("links error message via aria-describedby", () => {
    render(
      <FormField
        label="Username"
        name="username"
        error={{ type: "minLength", message: "Too short" }}
      />,
    );

    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("aria-describedby", "username-error");
    expect(screen.getByText("Too short")).toHaveAttribute("id", "username-error");
  });
});
