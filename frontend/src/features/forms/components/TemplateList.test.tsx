import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { TemplateList } from "./TemplateList";
import type { PaginatedResponse } from "@/types";
import type { FormTemplateList } from "@/types/forms";

const mockTemplate: FormTemplateList = {
  id: "tpl-1",
  name: "Application Form",
  slug: "application-form",
  description: "Standard application",
  owner_type: "business",
  scope: "business",
  status: "active",
  version: 1,
  is_current: true,
  is_template_public: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockData: PaginatedResponse<FormTemplateList> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockTemplate],
};

describe("TemplateList", () => {
  it("renders template items", () => {
    render(<TemplateList data={mockData} />);

    expect(screen.getByText("Application Form")).toBeInTheDocument();
    expect(screen.getByText("Standard application")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });

  it("shows loading skeletons", () => {
    const { container } = render(<TemplateList isLoading />);

    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(0);
  });

  it("shows empty state when no results", () => {
    render(
      <TemplateList
        data={{ count: 0, next: null, previous: null, results: [] }}
      />,
    );

    expect(screen.getByText("No templates found.")).toBeInTheDocument();
  });

  it("calls onTemplateClick when template is clicked", () => {
    const onClick = vi.fn();
    render(<TemplateList data={mockData} onTemplateClick={onClick} />);

    fireEvent.click(screen.getByText("Application Form"));
    expect(onClick).toHaveBeenCalledWith("tpl-1");
  });

  it("shows New Form button when canCreate is true", () => {
    render(<TemplateList data={mockData} canCreate />);

    expect(
      screen.getByRole("button", { name: "New Form" }),
    ).toBeInTheDocument();
  });

  it("hides New Form button when canCreate is false", () => {
    render(<TemplateList data={mockData} canCreate={false} />);

    expect(
      screen.queryByRole("button", { name: "New Form" }),
    ).not.toBeInTheDocument();
  });

  it("shows Public badge for public templates", () => {
    const publicTpl = { ...mockTemplate, is_template_public: true };
    render(
      <TemplateList
        data={{ ...mockData, results: [publicTpl] }}
      />,
    );

    expect(screen.getByText("Public")).toBeInTheDocument();
  });

  it("renders status filter tabs", () => {
    render(<TemplateList data={mockData} />);

    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Active" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Draft" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Archived" }),
    ).toBeInTheDocument();
  });
});
