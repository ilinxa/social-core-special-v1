import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { SocialLinksEditor } from "./SocialLinksEditor";

describe("SocialLinksEditor", () => {
  const defaultProps = {
    value: {} as Record<string, string>,
    onChange: vi.fn(),
  };

  it("renders 'No social links added yet.' when value is empty", () => {
    render(<SocialLinksEditor {...defaultProps} />);

    expect(screen.getByText("No social links added yet.")).toBeInTheDocument();
  });

  it("shows Add Link button", () => {
    render(<SocialLinksEditor {...defaultProps} />);

    expect(screen.getByRole("button", { name: /add link/i })).toBeInTheDocument();
  });

  it("renders platform select and URL input for each entry", () => {
    render(
      <SocialLinksEditor
        {...defaultProps}
        value={{ twitter: "https://twitter.com/test", facebook: "https://facebook.com/test" }}
      />,
    );

    const selects = screen.getAllByRole("combobox");
    expect(selects).toHaveLength(2);

    const inputs = screen.getAllByPlaceholderText("https://...");
    expect(inputs).toHaveLength(2);
  });

  it("calls onChange when add is clicked (adds first unused platform)", () => {
    const onChange = vi.fn();
    render(<SocialLinksEditor value={{}} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: /add link/i }));

    expect(onChange).toHaveBeenCalledWith({ twitter: "" });
  });

  it("adds the next unused platform when some are already used", () => {
    const onChange = vi.fn();
    render(
      <SocialLinksEditor
        value={{ twitter: "https://twitter.com/test" }}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /add link/i }));

    expect(onChange).toHaveBeenCalledWith({
      twitter: "https://twitter.com/test",
      facebook: "",
    });
  });

  it("calls onChange when remove is clicked (removes the platform)", () => {
    const onChange = vi.fn();
    render(
      <SocialLinksEditor
        value={{ twitter: "https://twitter.com/test", facebook: "https://facebook.com/test" }}
        onChange={onChange}
      />,
    );

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    fireEvent.click(removeButtons[0]);

    expect(onChange).toHaveBeenCalledWith({
      facebook: "https://facebook.com/test",
    });
  });

  it("calls onChange when URL changes", () => {
    const onChange = vi.fn();
    render(
      <SocialLinksEditor
        value={{ twitter: "" }}
        onChange={onChange}
      />,
    );

    const input = screen.getByPlaceholderText("https://...");
    fireEvent.change(input, { target: { value: "https://twitter.com/new" } });

    expect(onChange).toHaveBeenCalledWith({ twitter: "https://twitter.com/new" });
  });

  it("does not show Add Link when at max (10) links", () => {
    const maxLinks: Record<string, string> = {
      twitter: "https://twitter.com",
      facebook: "https://facebook.com",
      instagram: "https://instagram.com",
      linkedin: "https://linkedin.com",
      youtube: "https://youtube.com",
      tiktok: "https://tiktok.com",
      github: "https://github.com",
      website: "https://example.com",
      other: "https://other.com",
      extra: "https://extra.com",
    };

    render(<SocialLinksEditor value={maxLinks} onChange={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /add link/i })).not.toBeInTheDocument();
  });

  it("respects disabled state on Add Link button", () => {
    render(<SocialLinksEditor {...defaultProps} disabled />);

    expect(screen.getByRole("button", { name: /add link/i })).toBeDisabled();
  });

  it("respects disabled state on selects and inputs", () => {
    render(
      <SocialLinksEditor
        value={{ twitter: "https://twitter.com" }}
        onChange={vi.fn()}
        disabled
      />,
    );

    const select = screen.getByRole("combobox");
    expect(select).toBeDisabled();

    const input = screen.getByPlaceholderText("https://...");
    expect(input).toBeDisabled();

    const removeButton = screen.getByRole("button", { name: /remove/i });
    expect(removeButton).toBeDisabled();
  });

  it("does not show empty message when links exist", () => {
    render(
      <SocialLinksEditor
        value={{ twitter: "https://twitter.com" }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.queryByText("No social links added yet.")).not.toBeInTheDocument();
  });
});
