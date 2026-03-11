import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { Can } from "./Can";

describe("Can", () => {
  it("renders children when allowed is true", () => {
    render(
      <Can allowed={true}>
        <span>Edit button</span>
      </Can>,
    );

    expect(screen.getByText("Edit button")).toBeInTheDocument();
  });

  it("renders nothing when allowed is false", () => {
    const { container } = render(
      <Can allowed={false}>
        <span>Edit button</span>
      </Can>,
    );

    expect(screen.queryByText("Edit button")).not.toBeInTheDocument();
    expect(container.innerHTML).toBe("");
  });

  it("renders fallback when allowed is false and fallback provided", () => {
    render(
      <Can allowed={false} fallback={<span>No access</span>}>
        <span>Edit button</span>
      </Can>,
    );

    expect(screen.queryByText("Edit button")).not.toBeInTheDocument();
    expect(screen.getByText("No access")).toBeInTheDocument();
  });

  it("renders nothing when allowed is undefined", () => {
    const { container } = render(
      <Can allowed={undefined}>
        <span>Edit button</span>
      </Can>,
    );

    expect(screen.queryByText("Edit button")).not.toBeInTheDocument();
    expect(container.innerHTML).toBe("");
  });
});
