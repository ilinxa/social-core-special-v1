import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { useForm } from "react-hook-form";

import type { UsernameCheckResult } from "@/features/users/hooks/use-username-check";
import type { UsernameFormValues } from "@/lib/validations/profile";

const mockUsernameCheck = vi.fn<() => UsernameCheckResult>();

vi.mock("@/features/users/hooks/use-username-check", () => ({
  useUsernameCheck: () => mockUsernameCheck(),
}));

import { renderWithProviders } from "@/test/utils";

beforeEach(() => {
  vi.clearAllMocks();
  mockUsernameCheck.mockReturnValue({ isChecking: false, isAvailable: null, isCurrent: false });
});

describe("UsernameField", () => {
  async function renderField(checkResult: UsernameCheckResult) {
    mockUsernameCheck.mockReturnValue(checkResult);
    const { UsernameField } = await import("./UsernameField");

    function TestWrapper() {
      const { register, control, formState: { errors } } = useForm<UsernameFormValues>({
        defaultValues: {
          username: "testuser",
        },
      });

      return (
        <UsernameField
          control={control}
          currentUsername="testuser"
          error={errors.username}
          {...register("username")}
        />
      );
    }

    return renderWithProviders(<TestWrapper />);
  }

  it("renders username input with label", async () => {
    await renderField({ isChecking: false, isAvailable: null, isCurrent: false });

    expect(screen.getByLabelText("Username")).toBeInTheDocument();
  });

  it("shows Available text when username is available", async () => {
    await renderField({ isChecking: false, isAvailable: true, isCurrent: false });

    expect(screen.getByText("Available")).toBeInTheDocument();
  });

  it("shows Username taken text when unavailable", async () => {
    await renderField({ isChecking: false, isAvailable: false, isCurrent: false });

    expect(screen.getByText("Username taken")).toBeInTheDocument();
  });

  it("does not show status when not checked", async () => {
    await renderField({ isChecking: false, isAvailable: null, isCurrent: false });

    expect(screen.queryByText("Available")).not.toBeInTheDocument();
    expect(screen.queryByText("Username taken")).not.toBeInTheDocument();
  });

  it("does not show Available when username is current", async () => {
    await renderField({ isChecking: false, isAvailable: true, isCurrent: true });

    expect(screen.queryByText("Available")).not.toBeInTheDocument();
  });
});
