import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { ResponseList } from "./ResponseList";
import type { PaginatedResponse } from "@/types";
import type { FormResponseList } from "@/types/forms";

const mockResponse: FormResponseList = {
  id: "resp-1",
  form_template: "tpl-1",
  form_name: "Application Form",
  form_version: 1,
  submitted_by: "user-1",
  submitter_email: "alice@example.com",
  submitter_username: "alice",
  submitter_display_name: "Alice Smith",
  data: { full_name: "Alice Smith" },
  status: "submitted",
  submitted_at: "2026-01-02T00:00:00Z",
  processed_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const mockData: PaginatedResponse<FormResponseList> = {
  count: 1,
  next: null,
  previous: null,
  results: [mockResponse],
};

describe("ResponseList", () => {
  it("renders response items", () => {
    render(<ResponseList data={mockData} />);

    expect(screen.getByText("Application Form")).toBeInTheDocument();
    expect(screen.getByText(/alice@example\.com/)).toBeInTheDocument();
  });

  it("shows empty state when no results", () => {
    render(
      <ResponseList
        data={{ count: 0, next: null, previous: null, results: [] }}
      />,
    );

    expect(screen.getByText("No responses found.")).toBeInTheDocument();
  });

  it("calls onResponseClick when response is clicked", () => {
    const onClick = vi.fn();
    render(<ResponseList data={mockData} onResponseClick={onClick} />);

    fireEvent.click(screen.getByText("Application Form"));
    expect(onClick).toHaveBeenCalledWith("resp-1");
  });

  it("renders status filter tabs", () => {
    render(<ResponseList data={mockData} />);

    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Submitted" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Processed" }),
    ).toBeInTheDocument();
  });

  it("shows loading skeletons", () => {
    const { container } = render(<ResponseList isLoading />);

    expect(container.querySelectorAll("[data-slot='skeleton']").length).toBeGreaterThan(0);
  });
});
