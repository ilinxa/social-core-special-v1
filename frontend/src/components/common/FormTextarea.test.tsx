import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { FormTextarea } from "./FormTextarea";

describe("FormTextarea", () => {
  it("renders label and textarea", () => {
    render(<FormTextarea label="Bio" name="bio" />);

    expect(screen.getByLabelText("Bio")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("shows error message when error prop provided", () => {
    render(
      <FormTextarea
        label="Bio"
        name="bio"
        error={{ type: "required", message: "Bio is required" }}
      />,
    );

    expect(screen.getByText("Bio is required")).toBeInTheDocument();
  });

  it("shows description when no error", () => {
    render(
      <FormTextarea label="Bio" name="bio" description="Tell us about yourself" />,
    );

    expect(screen.getByText("Tell us about yourself")).toBeInTheDocument();
  });

  it("hides description when error is present", () => {
    render(
      <FormTextarea
        label="Bio"
        name="bio"
        description="Tell us about yourself"
        error={{ type: "maxLength", message: "Too long" }}
      />,
    );

    expect(screen.getByText("Too long")).toBeInTheDocument();
    expect(screen.queryByText("Tell us about yourself")).not.toBeInTheDocument();
  });

  it("sets aria-invalid when error exists", () => {
    render(
      <FormTextarea
        label="Bio"
        name="bio"
        error={{ type: "required", message: "Bio is required" }}
      />,
    );

    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("does not set aria-invalid when no error", () => {
    render(<FormTextarea label="Bio" name="bio" />);

    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "false");
  });

  it("links error message via aria-describedby", () => {
    render(
      <FormTextarea
        label="Description"
        name="description"
        error={{ type: "minLength", message: "Too short" }}
      />,
    );

    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveAttribute("aria-describedby", "description-error");
    expect(screen.getByText("Too short")).toHaveAttribute("id", "description-error");
  });

  it("does not set aria-describedby when no error", () => {
    render(<FormTextarea label="Bio" name="bio" />);

    expect(screen.getByRole("textbox")).not.toHaveAttribute("aria-describedby");
  });

  it("uses id prop over name for fieldId", () => {
    render(
      <FormTextarea label="Bio" name="bio" id="custom-id" />,
    );

    expect(screen.getByRole("textbox")).toHaveAttribute("id", "custom-id");
  });
});
