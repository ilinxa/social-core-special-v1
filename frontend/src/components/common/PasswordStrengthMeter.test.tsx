import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

describe("PasswordStrengthMeter", () => {
  it("renders nothing when password is empty", () => {
    const { container } = renderWithProviders(<PasswordStrengthMeter password="" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows Weak for a short lowercase-only password", () => {
    renderWithProviders(<PasswordStrengthMeter password="abc" />);
    expect(screen.getByText("Weak")).toBeInTheDocument();
  });

  it("shows Fair for a password meeting 3 criteria", () => {
    // 8+ chars, lowercase, number → 3 criteria met
    renderWithProviders(<PasswordStrengthMeter password="abcdefg1" />);
    expect(screen.getByText("Fair")).toBeInTheDocument();
  });

  it("shows Good for a password meeting 4 criteria", () => {
    // 8+ chars, lowercase, uppercase, number → 4 criteria met
    renderWithProviders(<PasswordStrengthMeter password="Abcdefg1" />);
    expect(screen.getByText("Good")).toBeInTheDocument();
  });

  it("shows Strong for a password meeting all 5 criteria", () => {
    // 8+ chars, lowercase, uppercase, number, special → 5 criteria met
    renderWithProviders(<PasswordStrengthMeter password="Abcdefg1!" />);
    expect(screen.getByText("Strong")).toBeInTheDocument();
  });

  it("displays all 5 criteria labels", () => {
    renderWithProviders(<PasswordStrengthMeter password="a" />);
    expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
    expect(screen.getByText("Contains uppercase letter")).toBeInTheDocument();
    expect(screen.getByText("Contains lowercase letter")).toBeInTheDocument();
    expect(screen.getByText("Contains a number")).toBeInTheDocument();
    expect(screen.getByText("Contains special character")).toBeInTheDocument();
  });
});
