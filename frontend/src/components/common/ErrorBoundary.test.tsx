import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { FeatureErrorBoundary } from "./ErrorBoundary";

vi.mock("@/lib/error-reporting", () => ({
  reportError: vi.fn(),
}));

import { reportError } from "@/lib/error-reporting";

function GoodChild() {
  return <div>Content rendered</div>;
}

function ThrowingChild({ message }: { message: string }): React.ReactNode {
  throw new Error(message);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FeatureErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <FeatureErrorBoundary>
        <GoodChild />
      </FeatureErrorBoundary>,
    );

    expect(screen.getByText("Content rendered")).toBeInTheDocument();
  });

  it("shows error fallback when child throws", () => {
    // Suppress React error boundary console.error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <FeatureErrorBoundary>
        <ThrowingChild message="Component crashed" />
      </FeatureErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Component crashed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();

    spy.mockRestore();
  });

  it("calls reportError when error occurs", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <FeatureErrorBoundary>
        <ThrowingChild message="Reporting test" />
      </FeatureErrorBoundary>,
    );

    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Reporting test" }),
      expect.objectContaining({ boundary: "feature" }),
    );

    spy.mockRestore();
  });

  it("resets and re-renders children on try again", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    let shouldThrow = true;

    function ConditionalChild() {
      if (shouldThrow) throw new Error("Temporary error");
      return <div>Recovered</div>;
    }

    render(
      <FeatureErrorBoundary>
        <ConditionalChild />
      </FeatureErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Fix the condition and click retry
    shouldThrow = false;
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    expect(screen.getByText("Recovered")).toBeInTheDocument();

    spy.mockRestore();
  });
});
