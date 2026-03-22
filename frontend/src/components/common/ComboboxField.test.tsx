import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ComboboxField } from "./ComboboxField";

const mockOptions = [
  { value: "us", label: "United States" },
  { value: "gb", label: "United Kingdom" },
  { value: "de", label: "Germany" },
] as const;

describe("ComboboxField", () => {
  it("renders with label", () => {
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
      />,
    );
    expect(screen.getByText("Country")).toBeInTheDocument();
  });

  it("opens popover on click", async () => {
    const user = userEvent.setup();
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
      />,
    );

    await user.click(screen.getByRole("combobox"));

    expect(screen.getByText("United States")).toBeInTheDocument();
    expect(screen.getByText("United Kingdom")).toBeInTheDocument();
    expect(screen.getByText("Germany")).toBeInTheDocument();
  });

  it("calls onChange when an option is selected", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={onChange}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
      />,
    );

    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByText("Germany"));

    expect(onChange).toHaveBeenCalledWith("de");
  });

  it("shows selected value label on the trigger", () => {
    render(
      <ComboboxField
        label="Country"
        value="gb"
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
      />,
    );

    expect(screen.getByRole("combobox")).toHaveTextContent("United Kingdom");
  });

  it("shows placeholder when no value selected", () => {
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
      />,
    );

    expect(screen.getByRole("combobox")).toHaveTextContent("Select country...");
  });

  it("displays error message", () => {
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
        error="Country is required"
      />,
    );

    expect(screen.getByText("Country is required")).toBeInTheDocument();
  });

  it("disables trigger when disabled prop is set", () => {
    render(
      <ComboboxField
        label="Country"
        value=""
        onChange={vi.fn()}
        options={mockOptions}
        searchPlaceholder="Search countries..."
        emptyText="No country found."
        disabled
      />,
    );

    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});
