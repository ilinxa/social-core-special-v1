import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FormTagInput } from "./FormTagInput";

vi.mock("@/hooks/use-tag-suggestions", () => ({
  useTagSuggestions: vi.fn(() => ({
    data: [
      { id: "1", name: "react", usage_count: 42 },
      { id: "2", name: "nextjs", usage_count: 28 },
      { id: "3", name: "typescript", usage_count: 35 },
    ],
  })),
}));

describe("FormTagInput", () => {
  it("renders with label", () => {
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={vi.fn()}
        category="user"
      />,
    );
    expect(screen.getByText("Tags")).toBeInTheDocument();
  });

  it("renders existing tags as badges", () => {
    render(
      <FormTagInput
        label="Tags"
        value={["react", "nextjs"]}
        onChange={vi.fn()}
        category="user"
      />,
    );

    expect(screen.getByText("react")).toBeInTheDocument();
    expect(screen.getByText("nextjs")).toBeInTheDocument();
  });

  it("adds a tag on Enter key", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={onChange}
        category="user"
      />,
    );

    const input = screen.getByPlaceholderText("Add tags...");
    await user.type(input, "newTag{Enter}");

    expect(onChange).toHaveBeenCalledWith(["newtag"]);
  });

  it("adds a tag on comma key", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={onChange}
        category="user"
      />,
    );

    const input = screen.getByPlaceholderText("Add tags...");
    await user.type(input, "frontend,");

    expect(onChange).toHaveBeenCalledWith(["frontend"]);
  });

  it("removes a tag when X button is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={["react", "nextjs"]}
        onChange={onChange}
        category="user"
      />,
    );

    const removeButtons = screen.getAllByRole("button");
    await user.click(removeButtons[0]);

    expect(onChange).toHaveBeenCalledWith(["nextjs"]);
  });

  it("does not add duplicate tags", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={["react"]}
        onChange={onChange}
        category="user"
      />,
    );

    const input = screen.getByRole("textbox");
    await user.type(input, "react{Enter}");

    expect(onChange).not.toHaveBeenCalled();
  });

  it("enforces maxTags limit", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={["a", "b"]}
        onChange={onChange}
        category="user"
        maxTags={2}
      />,
    );

    const input = screen.getByRole("textbox");
    await user.type(input, "c{Enter}");

    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes last tag on Backspace when input is empty", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={["react", "nextjs"]}
        onChange={onChange}
        category="user"
      />,
    );

    const input = screen.getByRole("textbox");
    await user.click(input);
    await user.keyboard("{Backspace}");

    expect(onChange).toHaveBeenCalledWith(["react"]);
  });

  it("shows suggestions when typing", async () => {
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={vi.fn()}
        category="user"
      />,
    );

    const input = screen.getByPlaceholderText("Add tags...");
    await user.type(input, "r");

    expect(screen.getByText("react")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("adds tag when suggestion is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={onChange}
        category="user"
      />,
    );

    const input = screen.getByPlaceholderText("Add tags...");
    await user.type(input, "r");

    const suggestion = screen.getByText("react");
    await user.click(suggestion);

    expect(onChange).toHaveBeenCalledWith(["react"]);
  });

  it("displays error message", () => {
    render(
      <FormTagInput
        label="Tags"
        value={[]}
        onChange={vi.fn()}
        category="user"
        error="At least one tag is required"
      />,
    );

    expect(screen.getByText("At least one tag is required")).toBeInTheDocument();
  });
});
