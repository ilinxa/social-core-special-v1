import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { FormBuilder } from "./FormBuilder";
import type { FormField } from "@/types/forms";

const textField: FormField = {
  id: "f1",
  field_key: "full_name",
  field_type: "text",
  label: "Full Name",
  description: "Enter your full name",
  placeholder: "John Doe",
  order: 0,
  step_tag: "",
  section_tag: "",
  options: [],
  validation_rules: {},
  ui_config: {},
  default_value: null,
  is_required: true,
  is_indexed: false,
  is_hidden: false,
  is_readonly: false,
};

const selectField: FormField = {
  id: "f2",
  field_key: "role",
  field_type: "select",
  label: "Preferred Role",
  description: "",
  placeholder: "Select a role",
  order: 1,
  step_tag: "",
  section_tag: "",
  options: [
    { value: "dev", label: "Developer" },
    { value: "pm", label: "Product Manager" },
  ],
  validation_rules: {},
  ui_config: {},
  default_value: null,
  is_required: false,
  is_indexed: false,
  is_hidden: false,
  is_readonly: false,
};

const boolField: FormField = {
  id: "f3",
  field_key: "agree",
  field_type: "boolean",
  label: "I agree to the terms",
  description: "",
  placeholder: "",
  order: 2,
  step_tag: "",
  section_tag: "",
  options: [],
  validation_rules: {},
  ui_config: {},
  default_value: null,
  is_required: true,
  is_indexed: false,
  is_hidden: false,
  is_readonly: false,
};

const hiddenField: FormField = {
  ...textField,
  id: "f4",
  field_key: "hidden_field",
  label: "Hidden",
  is_hidden: true,
};

const fields = [textField, selectField, boolField];

describe("FormBuilder", () => {
  describe("fill mode", () => {
    it("renders all visible fields", () => {
      render(<FormBuilder fields={fields} mode="fill" />);

      expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Preferred Role/)).toBeInTheDocument();
      expect(screen.getByLabelText(/I agree to the terms/)).toBeInTheDocument();
    });

    it("shows required indicator for required fields", () => {
      render(<FormBuilder fields={fields} mode="fill" />);

      const labels = screen.getAllByText("*");
      expect(labels).toHaveLength(2); // full_name + agree
    });

    it("calls onValuesChange when a field is edited", () => {
      const onValuesChange = vi.fn();
      render(
        <FormBuilder
          fields={[textField]}
          mode="fill"
          onValuesChange={onValuesChange}
        />,
      );

      fireEvent.change(screen.getByPlaceholderText("John Doe"), {
        target: { value: "Alice" },
      });

      expect(onValuesChange).toHaveBeenCalledWith({ full_name: "Alice" });
    });

    it("shows submit button and calls onSubmit", () => {
      const onSubmit = vi.fn();
      render(
        <FormBuilder
          fields={[textField]}
          mode="fill"
          values={{ full_name: "Alice" }}
          onSubmit={onSubmit}
          submitLabel="Save"
        />,
      );

      const btn = screen.getByRole("button", { name: "Save" });
      fireEvent.click(btn);

      expect(onSubmit).toHaveBeenCalledWith({ full_name: "Alice" });
    });

    it("shows validation errors", () => {
      render(
        <FormBuilder
          fields={[textField]}
          mode="fill"
          errors={{ full_name: "Name is required" }}
        />,
      );

      expect(screen.getByText("Name is required")).toBeInTheDocument();
    });
  });

  describe("view mode", () => {
    it("renders fields as disabled", () => {
      render(
        <FormBuilder
          fields={[textField]}
          mode="view"
          values={{ full_name: "Alice" }}
        />,
      );

      const input = screen.getByLabelText(/Full Name/) as HTMLInputElement;
      expect(input).toBeDisabled();
      expect(input.value).toBe("Alice");
    });

    it("does not show submit button", () => {
      render(<FormBuilder fields={[textField]} mode="view" />);

      expect(
        screen.queryByRole("button", { name: "Submit" }),
      ).not.toBeInTheDocument();
    });
  });

  describe("design mode", () => {
    it("renders add field panel", () => {
      const onAddField = vi.fn();
      render(
        <FormBuilder
          fields={[]}
          mode="design"
          onAddField={onAddField}
        />,
      );

      expect(screen.getByRole("button", { name: "Add Field" })).toBeInTheDocument();
    });

    it("opens edit panel when field is clicked", () => {
      render(
        <FormBuilder
          fields={[textField]}
          mode="design"
          onUpdateField={vi.fn()}
          onDeleteField={vi.fn()}
        />,
      );

      // Click on the field wrapper
      fireEvent.click(screen.getByText("Full Name"));

      // Should show edit panel with Delete button
      expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Save Changes" }),
      ).toBeInTheDocument();
    });
  });

  describe("hidden fields", () => {
    it("does not render hidden fields", () => {
      render(
        <FormBuilder fields={[textField, hiddenField]} mode="fill" />,
      );

      expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
      expect(screen.queryByText("Hidden")).not.toBeInTheDocument();
    });
  });

  describe("sections and steps", () => {
    it("groups fields by section_tag", () => {
      const sectionedFields: FormField[] = [
        { ...textField, section_tag: "Personal Info" },
        { ...selectField, section_tag: "Personal Info" },
        { ...boolField, section_tag: "Agreement" },
      ];

      render(<FormBuilder fields={sectionedFields} mode="fill" />);

      expect(screen.getByText("Personal Info")).toBeInTheDocument();
      expect(screen.getByText("Agreement")).toBeInTheDocument();
    });

    it("renders step tabs when fields have step_tags", () => {
      const steppedFields: FormField[] = [
        { ...textField, step_tag: "Step 1" },
        { ...selectField, step_tag: "Step 2" },
      ];

      render(<FormBuilder fields={steppedFields} mode="fill" />);

      expect(screen.getByRole("tab", { name: "Step 1" })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: "Step 2" })).toBeInTheDocument();
    });

    it("preserves Tab 1 values when switching to Tab 2 and back", () => {
      const steppedFields: FormField[] = [
        { ...textField, step_tag: "Step 1" },
        { ...selectField, step_tag: "Step 2" },
      ];

      render(<FormBuilder fields={steppedFields} mode="fill" />);

      // Fill Tab 1 field
      fireEvent.change(screen.getByPlaceholderText("John Doe"), {
        target: { value: "Alice" },
      });

      // Switch to Tab 2
      fireEvent.click(screen.getByRole("tab", { name: "Step 2" }));

      // Switch back to Tab 1
      fireEvent.click(screen.getByRole("tab", { name: "Step 1" }));

      // Tab 1 value should still be present
      const input = screen.getByPlaceholderText("John Doe") as HTMLInputElement;
      expect(input.value).toBe("Alice");
    });

    it("submits values from all tabs, not just the active one", () => {
      const onSubmit = vi.fn();
      const steppedFields: FormField[] = [
        { ...textField, step_tag: "Step 1", is_required: false },
        {
          ...selectField,
          step_tag: "Step 2",
          is_required: false,
          field_key: "role",
        },
      ];

      render(
        <FormBuilder
          fields={steppedFields}
          mode="fill"
          values={{ full_name: "Alice", role: "dev" }}
          onSubmit={onSubmit}
        />,
      );

      // Submit from Tab 1 (Tab 2 is hidden but values should still be included)
      fireEvent.click(screen.getByRole("button", { name: "Submit" }));

      expect(onSubmit).toHaveBeenCalledWith({
        full_name: "Alice",
        role: "dev",
      });
    });

    it("keeps hidden-tab fields mounted in the DOM", () => {
      const steppedFields: FormField[] = [
        { ...textField, step_tag: "Step 1" },
        { ...selectField, step_tag: "Step 2" },
      ];

      const { container } = render(
        <FormBuilder fields={steppedFields} mode="fill" />,
      );

      // Tab 1 is active — Tab 2 field should exist in DOM but be hidden
      const hiddenDiv = container.querySelector(".hidden");
      expect(hiddenDiv).toBeInTheDocument();
    });
  });
});
