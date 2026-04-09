import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { DateSeparator } from "../DateSeparator";

describe("DateSeparator", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders 'Today' for today's date", () => {
    // Mock current date as 2026-03-26 12:00:00
    vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));

    render(<DateSeparator date="2026-03-26T10:30:00Z" />);

    expect(screen.getByText("Today")).toBeInTheDocument();
  });

  it("renders 'Yesterday' for yesterday's date", () => {
    // Mock current date as 2026-03-26 12:00:00
    vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));

    render(<DateSeparator date="2026-03-25T10:30:00Z" />);

    expect(screen.getByText("Yesterday")).toBeInTheDocument();
  });

  it("renders formatted date for older dates", () => {
    // Mock current date as 2026-03-26 12:00:00
    vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));

    render(<DateSeparator date="2026-03-20T10:30:00Z" />);

    // Should show "Fri, Mar 20" (weekday short, month short, day numeric)
    expect(screen.getByText(/Fri.*Mar.*20/i)).toBeInTheDocument();
  });

  it("includes year when date is from a different year", () => {
    // Mock current date as 2026-03-26 12:00:00
    vi.setSystemTime(new Date("2026-03-26T12:00:00Z"));

    render(<DateSeparator date="2025-12-25T10:30:00Z" />);

    // Should show "Thu, Dec 25, 2025" (includes year)
    expect(screen.getByText(/2025/)).toBeInTheDocument();
    expect(screen.getByText(/Dec.*25.*2025/i)).toBeInTheDocument();
  });
});
