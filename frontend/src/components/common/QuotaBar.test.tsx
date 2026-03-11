import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { QuotaBar } from "./QuotaBar";

describe("QuotaBar", () => {
  it("renders current and max count", () => {
    render(<QuotaBar current={3} max={10} />);
    expect(screen.getByText("3 / 10")).toBeInTheDocument();
  });

  it("renders label", () => {
    render(<QuotaBar current={3} max={10} label="Team Members" />);
    expect(screen.getByText("Team Members")).toBeInTheDocument();
  });

  it("defaults label to Members", () => {
    render(<QuotaBar current={1} max={5} />);
    expect(screen.getByText("Members")).toBeInTheDocument();
  });

  it("shows Unlimited when max is 0", () => {
    render(<QuotaBar current={7} max={0} />);
    expect(screen.getByText("7 (Unlimited)")).toBeInTheDocument();
  });

  it("does not render progress bar when unlimited", () => {
    render(<QuotaBar current={3} max={0} />);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("renders progress bar when max > 0", () => {
    render(<QuotaBar current={5} max={10} />);
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("applies destructive style when full", () => {
    render(<QuotaBar current={10} max={10} />);
    const text = screen.getByText("10 / 10");
    expect(text.className).toContain("text-destructive");
  });

  it("applies warning style when near full (>= 80%)", () => {
    render(<QuotaBar current={8} max={10} />);
    const text = screen.getByText("8 / 10");
    expect(text.className).toContain("text-yellow-600");
  });

  it("does not apply warning style below 80%", () => {
    render(<QuotaBar current={7} max={10} />);
    const text = screen.getByText("7 / 10");
    expect(text.className).not.toContain("text-yellow-600");
    expect(text.className).not.toContain("text-destructive");
  });
});
